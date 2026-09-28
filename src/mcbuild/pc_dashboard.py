from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

APP_NAME = "GabCon GPU Control"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8899
MAX_LOG_LINES = 500

GPU_QUERY_FIELDS = [
    "index",
    "uuid",
    "name",
    "temperature.gpu",
    "utilization.gpu",
    "memory.used",
    "memory.total",
    "power.draw",
    "power.limit",
    "clocks.sm",
    "pcie.link.gen.current",
    "pcie.link.width.current",
]

GPU_QUERY_KEYS = [
    "index",
    "uuid",
    "name",
    "temperature_c",
    "utilization_pct",
    "memory_used_mib",
    "memory_total_mib",
    "power_draw_w",
    "power_limit_w",
    "clock_sm_mhz",
    "pcie_gen",
    "pcie_width",
]

PROCESS_QUERY_FIELDS = ["pid", "process_name", "gpu_uuid", "used_memory"]
PROCESS_QUERY_KEYS = ["pid", "process_name", "gpu_uuid", "used_memory_mib"]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _run(command: list[str], timeout: float = 5.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _clean_numeric(value: str) -> int | float | None:
    value = value.strip()
    if not value or value.upper() in {"N/A", "[N/A]", "NOT SUPPORTED"}:
        return None
    try:
        number = float(value)
    except ValueError:
        return None
    return int(number) if number.is_integer() else number


def _parse_csv_rows(text: str, keys: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in csv.reader(line for line in text.splitlines() if line.strip()):
        if len(row) < len(keys):
            row.extend([""] * (len(keys) - len(row)))
        item: dict[str, Any] = {}
        for key, raw in zip(keys, row, strict=False):
            raw = raw.strip()
            if key in {
                "index",
                "temperature_c",
                "utilization_pct",
                "memory_used_mib",
                "memory_total_mib",
                "power_draw_w",
                "power_limit_w",
                "clock_sm_mhz",
                "pcie_gen",
                "pcie_width",
                "pid",
                "used_memory_mib",
            }:
                item[key] = _clean_numeric(raw)
            else:
                item[key] = raw
        rows.append(item)
    return rows


def query_gpus() -> tuple[list[dict[str, Any]], str | None]:
    command = [
        "nvidia-smi",
        f"--query-gpu={','.join(GPU_QUERY_FIELDS)}",
        "--format=csv,noheader,nounits",
    ]
    try:
        result = _run(command)
    except FileNotFoundError:
        return [], "nvidia-smi introuvable. Vérifie le driver NVIDIA/WSL GPU passthrough."
    except subprocess.TimeoutExpired:
        return [], "nvidia-smi n'a pas répondu dans le délai imparti."
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "nvidia-smi a échoué"
        return [], message
    return _parse_csv_rows(result.stdout, GPU_QUERY_KEYS), None


def query_gpu_processes() -> list[dict[str, Any]]:
    command = [
        "nvidia-smi",
        f"--query-compute-apps={','.join(PROCESS_QUERY_FIELDS)}",
        "--format=csv,noheader,nounits",
    ]
    try:
        result = _run(command)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0 or not result.stdout.strip():
        return []
    return _parse_csv_rows(result.stdout, PROCESS_QUERY_KEYS)


def _read_linux_memory() -> dict[str, int] | None:
    path = Path("/proc/meminfo")
    if not path.exists():
        return None
    values: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        parts = value.strip().split()
        if parts and parts[0].isdigit():
            values[key] = int(parts[0]) * 1024
    total = values.get("MemTotal")
    available = values.get("MemAvailable")
    if total is None or available is None:
        return None
    return {"total_bytes": total, "used_bytes": total - available, "available_bytes": available}


def _disk_snapshot(path: Path) -> dict[str, Any]:
    usage = shutil.disk_usage(path)
    return {
        "path": str(path),
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
    }


def _is_wsl() -> bool:
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    version_path = Path("/proc/version")
    if not version_path.exists():
        return False
    text = version_path.read_text(encoding="utf-8", errors="replace").lower()
    return "microsoft" in text or "wsl" in text


def system_snapshot() -> dict[str, Any]:
    try:
        load = os.getloadavg()
    except (AttributeError, OSError):
        load = None
    home = Path.home()
    root = Path(home.anchor or "/")
    disks = [_disk_snapshot(home)]
    if root != home:
        root_disk = _disk_snapshot(root)
        if root_disk["total_bytes"] != disks[0]["total_bytes"]:
            disks.append(root_disk)
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "wsl": _is_wsl(),
        "wsl_distro": os.environ.get("WSL_DISTRO_NAME"),
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "load_average": list(load) if load else None,
        "memory": _read_linux_memory(),
        "disks": disks,
    }


@dataclass
class ManagedJob:
    id: str
    preset: str
    label: str
    gpu: str
    command: list[str]
    started_at: str
    process: subprocess.Popen[str] = field(repr=False)
    lines: deque[str] = field(default_factory=lambda: deque(maxlen=MAX_LOG_LINES), repr=False)
    returncode: int | None = None
    finished_at: str | None = None

    def public(self) -> dict[str, Any]:
        running = self.process.poll() is None
        if not running and self.returncode is None:
            self.returncode = self.process.returncode
            self.finished_at = self.finished_at or _now_iso()
        return {
            "id": self.id,
            "preset": self.preset,
            "label": self.label,
            "gpu": self.gpu,
            "command": self.command,
            "started_at": self.started_at,
            "running": running,
            "returncode": self.returncode,
            "finished_at": self.finished_at,
            "log": list(self.lines),
        }


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, ManagedJob] = {}
        self._lock = threading.Lock()

    def _preset(self, name: str) -> tuple[str, list[str]]:
        if name == "nvidia_smi":
            return "NVIDIA SMI snapshot", ["nvidia-smi"]
        if name == "torch_probe":
            script = (
                "import torch; "
                "print('PyTorch:', torch.__version__); "
                "print('CUDA runtime:', torch.version.cuda); "
                "print('CUDA available:', torch.cuda.is_available()); "
                "print('GPU count:', torch.cuda.device_count()); "
                "print('BF16 supported:', torch.cuda.is_bf16_supported()); "
                "[(print(f'GPU {i}: {torch.cuda.get_device_name(i)}'), "
                "print(f'VRAM: {torch.cuda.get_device_properties(i).total_memory / 1024**3:.2f} GiB')) "
                "for i in range(torch.cuda.device_count())]"
            )
            return "PyTorch GPU probe", [sys.executable, "-c", script]
        if name == "bitsandbytes_probe":
            script = (
                "import torch; import bitsandbytes as bnb; "
                "print('torch:', torch.__version__); "
                "print('bitsandbytes:', bnb.__version__); "
                "print('cuda:', torch.version.cuda); "
                "print('gpu:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"
            )
            return "bitsandbytes 4-bit probe", [sys.executable, "-c", script]
        raise ValueError("Preset inconnu")

    @staticmethod
    def _normalize_gpu(gpu: Any) -> str:
        if gpu in (None, "", "all"):
            return "all"
        if isinstance(gpu, int) and gpu >= 0:
            return str(gpu)
        if isinstance(gpu, str) and gpu.isdigit():
            return gpu
        raise ValueError("GPU invalide")

    def start(self, preset: str, gpu: Any = "all") -> dict[str, Any]:
        gpu_value = self._normalize_gpu(gpu)
        label, command = self._preset(preset)
        env = os.environ.copy()
        if gpu_value != "all":
            env["CUDA_VISIBLE_DEVICES"] = gpu_value
        creationflags = 0
        start_new_session = os.name != "nt"
        if os.name == "nt":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
            start_new_session=start_new_session,
            creationflags=creationflags,
        )
        job = ManagedJob(
            id=uuid.uuid4().hex[:10],
            preset=preset,
            label=label,
            gpu=gpu_value,
            command=command,
            started_at=_now_iso(),
            process=process,
        )
        with self._lock:
            self._jobs[job.id] = job
        threading.Thread(target=self._capture, args=(job,), daemon=True).start()
        return job.public()

    def _capture(self, job: ManagedJob) -> None:
        stream = job.process.stdout
        if stream is not None:
            for line in stream:
                job.lines.append(line.rstrip("\n"))
        job.returncode = job.process.wait()
        job.finished_at = _now_iso()

    def stop(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)
        if job.process.poll() is None:
            if os.name == "nt":
                job.process.terminate()
            else:
                try:
                    os.killpg(job.process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        return job.public()

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            jobs = list(self._jobs.values())
        return [job.public() for job in reversed(jobs)]


DASHBOARD_HTML = r'''<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GabCon GPU Control</title>
<style>
:root{color-scheme:dark;--bg:#090b10;--panel:#11151d;--panel2:#151a24;--line:#252c39;--text:#eef3ff;
--muted:#8f9bad;--green:#7cf6b3;--cyan:#67d4ff;--amber:#ffcc66;--red:#ff7b87;--violet:#bfa0ff}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 20% 0,#142033 0,transparent 34%),var(--bg);
font:14px/1.45 ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif;color:var(--text)}button,select{font:inherit}
.shell{max-width:1480px;margin:auto;padding:20px}.top{display:flex;align-items:center;justify-content:space-between;gap:14px;
margin-bottom:18px}.brand{display:flex;align-items:center;gap:12px}.logo{width:42px;height:42px;border:1px solid #39506d;
border-radius:13px;display:grid;place-items:center;background:linear-gradient(145deg,#162438,#0e141e);box-shadow:0 0 30px #2c8fb02a;
font-weight:800;color:var(--cyan)}h1{font-size:18px;margin:0}.subtitle{color:var(--muted);font-size:12px}.pill{display:inline-flex;
align-items:center;gap:7px;border:1px solid var(--line);background:#0d1118;padding:6px 9px;border-radius:999px;color:var(--muted)}
.dot{width:8px;height:8px;border-radius:50%;background:var(--green);box-shadow:0 0 12px var(--green)}.grid{display:grid;gap:14px}
.summary{grid-template-columns:repeat(4,minmax(0,1fr));margin-bottom:14px}.card{border:1px solid var(--line);background:linear-gradient(180deg,#131924e8,#0e1219e8);
border-radius:16px;box-shadow:0 16px 50px #0005}.metric{padding:15px}.metric b{display:block;font-size:22px;margin-top:6px}.label{font-size:11px;
text-transform:uppercase;letter-spacing:.1em;color:var(--muted)}.gpu-grid{grid-template-columns:repeat(2,minmax(0,1fr));margin-bottom:14px}
.gpu{padding:16px}.gpuhead{display:flex;justify-content:space-between;gap:16px;margin-bottom:15px}.gpu h2{font-size:15px;margin:0 0 3px}.mono{font-family:
ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}.small{font-size:12px;color:var(--muted)}.bars{display:grid;gap:10px}.barrow{display:grid;
grid-template-columns:90px 1fr 70px;align-items:center;gap:10px}.track{height:8px;background:#202735;border-radius:999px;overflow:hidden}.fill{height:100%;
border-radius:999px;background:linear-gradient(90deg,var(--cyan),var(--violet));transition:width .3s ease}.facts{display:grid;grid-template-columns:repeat(4,1fr);
gap:8px;margin-top:14px}.fact{border:1px solid var(--line);background:#0d1118;padding:9px;border-radius:10px}.fact b{display:block;font-size:13px;margin-top:3px}
.actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}.btn{border:1px solid #344155;background:#171e29;color:var(--text);padding:8px 11px;border-radius:10px;
cursor:pointer}.btn:hover{border-color:#55708f;background:#1b2533}.btn.danger{border-color:#63323a;color:#ffb5bd}.btn.primary{border-color:#27617a;background:#102630;color:#b8ecff}
.lower{grid-template-columns:minmax(0,1.2fr) minmax(320px,.8fr)}.section{padding:16px}.section h3{font-size:14px;margin:0 0 12px}.tablewrap{overflow:auto}
table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:9px 8px;border-bottom:1px solid var(--line);font-size:12px}th{color:var(--muted);font-weight:600}
.empty{color:var(--muted);padding:20px 0;text-align:center}.jobs{display:grid;gap:9px}.job{border:1px solid var(--line);background:#0d1118;border-radius:12px;padding:11px}
.jobhead{display:flex;justify-content:space-between;gap:12px}.status{font-size:11px}.running{color:var(--green)}.failed{color:var(--red)}.done{color:var(--muted)}
pre{white-space:pre-wrap;word-break:break-word;max-height:210px;overflow:auto;background:#080b10;border:1px solid #1f2632;border-radius:9px;padding:9px;color:#cbd8e8;
font-size:11px}.error{border-color:#6e3139!important}.warning{color:var(--amber)}.cmd{display:flex;gap:8px;align-items:center;border:1px solid var(--line);background:#090d13;
padding:10px;border-radius:10px}.cmd code{flex:1;overflow:auto;color:#caeaff}.footer{margin-top:14px;color:var(--muted);font-size:11px;text-align:center}
@media(max-width:900px){.summary{grid-template-columns:repeat(2,1fr)}.gpu-grid,.lower{grid-template-columns:1fr}.facts{grid-template-columns:repeat(2,1fr)}}
@media(max-width:520px){.shell{padding:12px}.top{align-items:flex-start;flex-direction:column}.summary{grid-template-columns:1fr 1fr}.barrow{grid-template-columns:74px 1fr 58px}}
</style>
</head>
<body>
<div class="shell">
  <div class="top"><div class="brand"><div class="logo">GC</div><div><h1>GabCon GPU Control</h1><div class="subtitle">2× RTX workstation · local dashboard</div></div></div>
  <div class="pill"><span class="dot"></span><span id="connection">API locale</span></div></div>
  <div class="grid summary">
    <div class="card metric"><span class="label">GPU détectés</span><b id="gpuCount">—</b><span class="small" id="gpuNames">nvidia-smi</span></div>
    <div class="card metric"><span class="label">VRAM utilisée</span><b id="vramTotal">—</b><span class="small">somme des GPU</span></div>
    <div class="card metric"><span class="label">RAM système</span><b id="ram">—</b><span class="small" id="ramSub">—</span></div>
    <div class="card metric"><span class="label">Environnement</span><b id="env">—</b><span class="small" id="host">—</span></div>
  </div>
  <div class="grid gpu-grid" id="gpuGrid"></div>
  <div class="grid lower">
    <div class="card section"><h3>Processus CUDA</h3><div class="tablewrap"><table><thead><tr><th>PID</th><th>GPU</th><th>Processus</th><th>VRAM</th></tr></thead><tbody id="procBody"></tbody></table></div></div>
    <div class="card section"><h3>Commande Qwen3.5 recommandée</h3><div class="small" style="margin-bottom:8px">Copie la commande avec le GPU choisi. L'interface ne l'exécute pas arbitrairement.</div>
      <div class="cmd"><code id="qwenCmd"></code><button class="btn" onclick="copyQwen()">Copier</button></div>
      <div class="actions"><button class="btn" onclick="selectQwenGpu(0)">GPU 0</button><button class="btn" onclick="selectQwenGpu(1)">GPU 1</button></div>
      <div class="small" style="margin-top:10px">Le dashboard reste sur <span class="mono">127.0.0.1</span> par défaut et les actions POST exigent un token de session.</div>
    </div>
    <div class="card section"><h3>Jobs lancés depuis le dashboard</h3><div class="jobs" id="jobs"></div></div>
    <div class="card section"><h3>Système / stockage</h3><div id="systemFacts"></div></div>
  </div>
  <div class="footer">GabCon BuildAI · actions whitelistées · aucune commande shell arbitraire exposée</div>
</div>
<script>
const TOKEN = __TOKEN__;
let qwenGpu = 0;
const fmtBytes = n => { if(n==null)return '—'; const u=['B','KiB','MiB','GiB','TiB']; let i=0,x=n; while(x>=1024&&i<u.length-1){x/=1024;i++} return `${x.toFixed(i>2?1:2)} ${u[i]}`; };
const pct = (a,b) => b ? Math.max(0,Math.min(100,(a/b)*100)) : 0;
const escapeHtml = s => String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
async function api(path, options={}){ const r=await fetch(path,options); if(!r.ok){let m=`HTTP ${r.status}`;try{m=(await r.json()).error||m}catch{} throw new Error(m)} return r.json(); }
function qwenCommand(){return `export CUDA_VISIBLE_DEVICES=${qwenGpu}\nexport PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True\n\nswift infer \\\n  --model Qwen/Qwen3.5-4B \\\n  --use_hf true \\\n  --infer_backend transformers \\\n  --quant_method bnb \\\n  --quant_bits 4 \\\n  --torch_dtype bfloat16 \\\n  --enable_thinking false \\\n  --max_new_tokens 128`;}
function selectQwenGpu(i){qwenGpu=i;document.getElementById('qwenCmd').textContent=qwenCommand()}
async function copyQwen(){await navigator.clipboard.writeText(qwenCommand())}
async function startJob(preset,gpu){await api('/api/jobs/start',{method:'POST',headers:{'Content-Type':'application/json','X-Mcbuild-Token':TOKEN},body:JSON.stringify({preset,gpu})}); await refreshJobs()}
async function stopJob(id){await api(`/api/jobs/${id}/stop`,{method:'POST',headers:{'Content-Type':'application/json','X-Mcbuild-Token':TOKEN},body:'{}'});await refreshJobs()}
function gpuCard(g){const mem=pct(g.memory_used_mib,g.memory_total_mib), util=g.utilization_pct??0, temp=g.temperature_c??0;return `<div class="card gpu">
<div class="gpuhead"><div><h2>GPU ${escapeHtml(g.index)} · ${escapeHtml(g.name)}</h2><div class="small mono">${escapeHtml(g.uuid)}</div></div><div class="pill"><span class="dot"></span>${temp||'—'}°C</div></div>
<div class="bars"><div class="barrow"><span>GPU</span><div class="track"><div class="fill" style="width:${util}%"></div></div><b>${util}%</b></div>
<div class="barrow"><span>VRAM</span><div class="track"><div class="fill" style="width:${mem}%"></div></div><b>${mem.toFixed(0)}%</b></div></div>
<div class="facts"><div class="fact"><span class="label">VRAM</span><b>${g.memory_used_mib??'—'} / ${g.memory_total_mib??'—'} MiB</b></div>
<div class="fact"><span class="label">Puissance</span><b>${g.power_draw_w??'—'} / ${g.power_limit_w??'—'} W</b></div>
<div class="fact"><span class="label">Clock SM</span><b>${g.clock_sm_mhz??'—'} MHz</b></div><div class="fact"><span class="label">PCIe</span><b>Gen ${g.pcie_gen??'—'} ×${g.pcie_width??'—'}</b></div></div>
<div class="actions"><button class="btn primary" onclick="startJob('torch_probe',${g.index})">Test PyTorch</button><button class="btn" onclick="startJob('bitsandbytes_probe',${g.index})">Test bitsandbytes</button><button class="btn" onclick="startJob('nvidia_smi',${g.index})">nvidia-smi</button></div></div>`}
function renderStatus(d){const g=d.gpus||[];document.getElementById('gpuCount').textContent=g.length;document.getElementById('gpuNames').textContent=g.length?g.map(x=>x.name).join(' · '):(d.gpu_error||'Aucun GPU');
const used=g.reduce((a,x)=>a+(x.memory_used_mib||0),0),total=g.reduce((a,x)=>a+(x.memory_total_mib||0),0);document.getElementById('vramTotal').textContent=total?`${(used/1024).toFixed(1)} / ${(total/1024).toFixed(1)} GiB`:'—';
const m=d.system.memory;document.getElementById('ram').textContent=m?`${fmtBytes(m.used_bytes)} / ${fmtBytes(m.total_bytes)}`:'—';document.getElementById('ramSub').textContent=m?`${pct(m.used_bytes,m.total_bytes).toFixed(0)}% utilisée`:'indisponible';
document.getElementById('env').textContent=d.system.wsl?(d.system.wsl_distro||'WSL'):'Native';document.getElementById('host').textContent=d.system.hostname;
const grid=document.getElementById('gpuGrid');grid.innerHTML=g.length?g.map(gpuCard).join(''):`<div class="card section error"><b>GPU indisponible</b><div class="small">${escapeHtml(d.gpu_error||'nvidia-smi n’a retourné aucune carte.')}</div></div>`;
const uuidToIndex=Object.fromEntries(g.map(x=>[x.uuid,x.index]));document.getElementById('procBody').innerHTML=(d.processes||[]).length?(d.processes.map(p=>`<tr><td class="mono">${p.pid??'—'}</td><td>${uuidToIndex[p.gpu_uuid]??'—'}</td><td>${escapeHtml(p.process_name)}</td><td>${p.used_memory_mib??'—'} MiB</td></tr>`).join('')):`<tr><td colspan="4" class="empty">Aucun processus CUDA compute détecté</td></tr>`;
const sf=document.getElementById('systemFacts');const disks=(d.system.disks||[]).map(x=>`<div class="fact"><span class="label">Disque ${escapeHtml(x.path)}</span><b>${fmtBytes(x.free_bytes)} libres</b><span class="small">${fmtBytes(x.used_bytes)} utilisés / ${fmtBytes(x.total_bytes)}</span></div>`).join('');sf.innerHTML=`<div class="facts" style="grid-template-columns:1fr 1fr"><div class="fact"><span class="label">Python</span><b>${escapeHtml(d.system.python)}</b></div><div class="fact"><span class="label">CUDA_VISIBLE_DEVICES</span><b>${escapeHtml(d.system.cuda_visible_devices??'non défini')}</b></div>${disks}</div>`;}
function renderJobs(jobs){const el=document.getElementById('jobs');if(!jobs.length){el.innerHTML='<div class="empty">Aucun job lancé ici</div>';return}el.innerHTML=jobs.map(j=>{const cls=j.running?'running':(j.returncode===0?'done':'failed');const st=j.running?'EN COURS':(j.returncode===0?'TERMINÉ':`ERREUR ${j.returncode}`);const logs=(j.log||[]).slice(-80).join('\n');return `<div class="job"><div class="jobhead"><div><b>${escapeHtml(j.label)}</b><div class="small mono">GPU ${escapeHtml(j.gpu)} · ${escapeHtml(j.id)}</div></div><div class="status ${cls}">${st}</div></div>${logs?`<pre>${escapeHtml(logs)}</pre>`:''}${j.running?`<button class="btn danger" onclick="stopJob('${j.id}')">Arrêter</button>`:''}</div>`}).join('')}
async function refreshStatus(){try{const d=await api('/api/status');renderStatus(d);document.getElementById('connection').textContent='API locale · connectée'}catch(e){document.getElementById('connection').textContent='API erreur';}}
async function refreshJobs(){try{renderJobs((await api('/api/jobs')).jobs||[])}catch{}}
selectQwenGpu(0);refreshStatus();refreshJobs();setInterval(refreshStatus,2000);setInterval(refreshJobs,1500);
</script>
</body>
</html>'''


class DashboardApp:
    def __init__(self) -> None:
        self.jobs = JobManager()
        self.token = secrets.token_urlsafe(24)

    def status(self) -> dict[str, Any]:
        gpus, gpu_error = query_gpus()
        return {
            "timestamp": _now_iso(),
            "gpus": gpus,
            "gpu_error": gpu_error,
            "processes": query_gpu_processes(),
            "system": system_snapshot(),
        }


class DashboardHandler(BaseHTTPRequestHandler):
    app: DashboardApp
    server_version = "GabConDashboard/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("[dashboard] " + (fmt % args) + "\n")

    def _json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _html(self, body: str) -> None:
        data = body.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 64 * 1024:
            raise ValueError("Payload trop grand")
        raw = self.rfile.read(length) if length else b"{}"
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Objet JSON attendu")
        return value

    def _authorized(self) -> bool:
        return secrets.compare_digest(self.headers.get("X-Mcbuild-Token", ""), self.app.token)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/":
            token_json = json.dumps(self.app.token)
            self._html(DASHBOARD_HTML.replace("__TOKEN__", token_json))
            return
        if path == "/api/status":
            self._json(self.app.status())
            return
        if path == "/api/jobs":
            self._json({"jobs": self.app.jobs.list()})
            return
        if path == "/api/health":
            self._json({"ok": True, "app": APP_NAME})
            return
        self._json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        if not self._authorized():
            self._json({"error": "Token de session invalide"}, HTTPStatus.FORBIDDEN)
            return
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
            if path == "/api/jobs/start":
                self._json(self.app.jobs.start(str(payload.get("preset", "")), payload.get("gpu", "all")))
                return
            if path.startswith("/api/jobs/") and path.endswith("/stop"):
                parts = path.strip("/").split("/")
                if len(parts) == 4:
                    self._json(self.app.jobs.stop(parts[2]))
                    return
            self._json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
        except KeyError:
            self._json({"error": "Job introuvable"}, HTTPStatus.NOT_FOUND)
        except (ValueError, json.JSONDecodeError) as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except FileNotFoundError as exc:
            self._json({"error": f"Commande introuvable: {exc.filename}"}, HTTPStatus.BAD_REQUEST)


def build_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> ThreadingHTTPServer:
    app = DashboardApp()
    handler = type("BoundDashboardHandler", (DashboardHandler,), {"app": app})
    return ThreadingHTTPServer((host, port), handler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Local dashboard for GabCon's NVIDIA workstation")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"HTTP port (default: {DEFAULT_PORT})")
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        print("WARNING: dashboard exposed beyond localhost. There is no user authentication.", file=sys.stderr)
    server = build_server(args.host, args.port)
    display_host = "127.0.0.1" if args.host in {"0.0.0.0", "::"} else args.host
    print(f"{APP_NAME}: http://{display_host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
