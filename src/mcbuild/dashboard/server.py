# ruff: noqa: E501
"""Zero-extra-dependency local dashboard for the GabCon dual-GPU workstation."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from mcbuild.dashboard.ui import DASHBOARD_HTML

_GPU_FIELDS = (
    "index",
    "name",
    "uuid",
    "temperature.gpu",
    "utilization.gpu",
    "utilization.memory",
    "memory.used",
    "memory.total",
    "power.draw",
    "power.limit",
    "clocks.current.graphics",
    "driver_version",
)

_DIAGNOSTICS = {"nvidia", "topology", "pcie", "pytorch", "bitsandbytes", "swift"}


def _run(command: list[str], *, timeout: float = 8.0, env: dict[str, str] | None = None) -> dict[str, Any]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
    except FileNotFoundError:
        return {
            "ok": False,
            "command": command,
            "returncode": None,
            "stdout": "",
            "stderr": f"Command not found: {command[0]}",
            "duration_ms": round((time.monotonic() - started) * 1000),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "command": command,
            "returncode": None,
            "stdout": exc.stdout or "",
            "stderr": f"Timed out after {timeout:.1f}s",
            "duration_ms": round((time.monotonic() - started) * 1000),
        }
    return {
        "ok": result.returncode == 0,
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "duration_ms": round((time.monotonic() - started) * 1000),
    }


def _as_number(value: str) -> int | float | str | None:
    value = value.strip()
    if value in {"", "N/A", "[N/A]", "Not Supported"}:
        return None
    try:
        number = float(value)
    except ValueError:
        return value
    return int(number) if number.is_integer() else number


def parse_gpu_csv(text: str, fields: tuple[str, ...] = _GPU_FIELDS) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    reader = csv.reader(io.StringIO(text))
    for raw in reader:
        if not raw:
            continue
        values = [_as_number(value) for value in raw]
        if len(values) != len(fields):
            continue
        rows.append(dict(zip(fields, values, strict=True)))
    return rows


def _gpu_snapshot() -> dict[str, Any]:
    query = ",".join(_GPU_FIELDS)
    result = _run(["nvidia-smi", f"--query-gpu={query}", "--format=csv,noheader,nounits"])
    if not result["ok"]:
        return {"available": False, "gpus": [], "error": result["stderr"] or result["stdout"]}

    gpus = parse_gpu_csv(result["stdout"])
    pcie = _run(
        [
            "nvidia-smi",
            "--query-gpu=index,pcie.link.gen.current,pcie.link.width.current",
            "--format=csv,noheader,nounits",
        ]
    )
    if pcie["ok"]:
        by_index: dict[int, tuple[Any, Any]] = {}
        for row in csv.reader(io.StringIO(pcie["stdout"])):
            if len(row) != 3:
                continue
            index = _as_number(row[0])
            if isinstance(index, int):
                by_index[index] = (_as_number(row[1]), _as_number(row[2]))
        for gpu in gpus:
            index = gpu.get("index")
            if isinstance(index, int) and index in by_index:
                gpu["pcie.link.gen.current"], gpu["pcie.link.width.current"] = by_index[index]

    apps = _run(
        [
            "nvidia-smi",
            "--query-compute-apps=pid,process_name,used_memory,gpu_uuid",
            "--format=csv,noheader,nounits",
        ]
    )
    processes: list[dict[str, Any]] = []
    if apps["ok"]:
        for row in csv.reader(io.StringIO(apps["stdout"])):
            if len(row) != 4:
                continue
            processes.append(
                {
                    "pid": _as_number(row[0]),
                    "name": row[1].strip(),
                    "memory_mb": _as_number(row[2]),
                    "gpu_uuid": row[3].strip(),
                }
            )
    return {"available": True, "gpus": gpus, "compute_processes": processes, "error": None}


def parse_meminfo(text: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        parts = value.strip().split()
        if not parts or not parts[0].isdigit():
            continue
        kib = int(parts[0])
        result[key] = kib * 1024
    return result


def _memory_snapshot() -> dict[str, Any]:
    try:
        info = parse_meminfo(Path("/proc/meminfo").read_text(encoding="utf-8"))
        total = info.get("MemTotal", 0)
        available = info.get("MemAvailable", 0)
        used = max(0, total - available)
        return {
            "total_bytes": total,
            "available_bytes": available,
            "used_bytes": used,
            "used_percent": round((used / total) * 100, 1) if total else None,
        }
    except OSError:
        return {"total_bytes": None, "available_bytes": None, "used_bytes": None, "used_percent": None}


def _cpu_snapshot() -> dict[str, Any]:
    load = None
    with contextlib.suppress(OSError):
        load = [round(value, 2) for value in os.getloadavg()]
    uptime = None
    with contextlib.suppress(OSError, ValueError, IndexError):
        uptime = float(Path("/proc/uptime").read_text(encoding="utf-8").split()[0])
    return {"logical_cpus": os.cpu_count(), "load_average": load, "uptime_seconds": uptime}


def _disk_snapshot() -> list[dict[str, Any]]:
    candidates = [("Linux /", Path("/")), ("Windows C:", Path("/mnt/c")), ("Windows D:", Path("/mnt/d"))]
    disks: list[dict[str, Any]] = []
    for label, path in candidates:
        if not path.exists():
            continue
        try:
            usage = shutil.disk_usage(path)
        except OSError:
            continue
        disks.append(
            {
                "label": label,
                "path": str(path),
                "total_bytes": usage.total,
                "used_bytes": usage.used,
                "free_bytes": usage.free,
                "used_percent": round((usage.used / usage.total) * 100, 1) if usage.total else None,
            }
        )
    return disks


def _detect_train_python() -> str:
    configured = os.getenv("MCBUILD_TRAIN_PYTHON")
    if configured:
        return str(Path(configured).expanduser())
    candidates = [
        Path.cwd() / ".venv-train" / "bin" / "python",
        Path(__file__).resolve().parents[3] / ".venv-train" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable


def _diagnostic(name: str) -> dict[str, Any]:
    if name not in _DIAGNOSTICS:
        return {"ok": False, "stderr": f"Unsupported diagnostic: {name}", "stdout": "", "command": []}
    if name == "nvidia":
        return _run(["nvidia-smi"], timeout=12)
    if name == "topology":
        return _run(["nvidia-smi", "topo", "-m"], timeout=12)
    if name == "pcie":
        return _run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,pcie.link.gen.current,pcie.link.width.current,pcie.link.gen.max,pcie.link.width.max",
                "--format=csv,noheader",
            ],
            timeout=12,
        )
    if name == "swift":
        swift = shutil.which("swift")
        if not swift:
            return {"ok": False, "stderr": "swift CLI not found in PATH", "stdout": "", "command": ["swift", "--version"]}
        return _run([swift, "--version"], timeout=12)

    python = _detect_train_python()
    if name == "pytorch":
        code = """import torch
print('PyTorch:', torch.__version__)
print('CUDA runtime:', torch.version.cuda)
print('CUDA available:', torch.cuda.is_available())
print('GPU count:', torch.cuda.device_count())
print('BF16 supported:', torch.cuda.is_bf16_supported())
for i in range(torch.cuda.device_count()):
 p=torch.cuda.get_device_properties(i); print(f'GPU {i}: {p.name} | VRAM {p.total_memory/1024**3:.2f} GiB | CC {p.major}.{p.minor}')"""
        return _run([python, "-c", code], timeout=25)
    code = """import torch
import bitsandbytes as bnb
print('torch:', torch.__version__)
print('bitsandbytes:', bnb.__version__)
print('cuda:', torch.version.cuda)
print('gpu:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"""
    return _run([python, "-c", code], timeout=25)


@dataclass
class ManagedJob:
    name: str
    process: subprocess.Popen[str]
    command: list[str]
    started_at: float
    log_path: Path


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, ManagedJob] = {}
        self._lock = threading.Lock()
        self.log_dir = Path(".mcbuild/dashboard/logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _refresh(self) -> None:
        dead = [name for name, job in self._jobs.items() if job.process.poll() is not None]
        for name in dead:
            self._jobs.pop(name, None)

    def status(self) -> list[dict[str, Any]]:
        with self._lock:
            self._refresh()
            return [
                {
                    "name": job.name,
                    "pid": job.process.pid,
                    "command": job.command,
                    "started_at": job.started_at,
                    "running": True,
                }
                for job in self._jobs.values()
            ]

    def start_mcbuild_server(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._refresh()
            if "mcbuild-server" in self._jobs:
                return {"ok": False, "error": "mcbuild-server is already running."}

            model = str(payload.get("model") or "anthropic/claude-sonnet-5")[:160]
            reasoning = str(payload.get("reasoning") or "off")
            if reasoning not in {"off", "low", "medium", "high"}:
                return {"ok": False, "error": "reasoning must be off, low, medium or high."}
            try:
                max_iters = int(payload.get("max_iters", 6))
            except (TypeError, ValueError):
                return {"ok": False, "error": "max_iters must be an integer."}
            if not 1 <= max_iters <= 30:
                return {"ok": False, "error": "max_iters must be between 1 and 30."}
            gpu = str(payload.get("gpu") or "")
            if gpu not in {"", "0", "1", "0,1"}:
                return {"ok": False, "error": "gpu must be blank, 0, 1 or 0,1."}

            command = [
                sys.executable,
                "-m",
                "mcbuild.server.ws_server",
                "--host",
                "127.0.0.1",
                "--port",
                "8765",
                "--model",
                model,
                "--max-iters",
                str(max_iters),
                "--reasoning",
                reasoning,
            ]
            env = os.environ.copy()
            if gpu:
                env["CUDA_VISIBLE_DEVICES"] = gpu
            log_path = self.log_dir / "mcbuild-server.log"
            log = log_path.open("a", encoding="utf-8")
            log.write(f"\n\n=== dashboard start {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            log.flush()
            try:
                process = subprocess.Popen(
                    command,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=env,
                    start_new_session=True,
                )
            except OSError as exc:
                log.close()
                return {"ok": False, "error": str(exc)}
            log.close()
            self._jobs["mcbuild-server"] = ManagedJob(
                name="mcbuild-server",
                process=process,
                command=command,
                started_at=time.time(),
                log_path=log_path,
            )
            return {"ok": True, "pid": process.pid, "command": command}

    def stop(self, name: str) -> dict[str, Any]:
        if name != "mcbuild-server":
            return {"ok": False, "error": "Unsupported managed job."}
        with self._lock:
            self._refresh()
            job = self._jobs.get(name)
            if not job:
                return {"ok": False, "error": f"{name} is not running."}
            try:
                os.killpg(job.process.pid, signal.SIGTERM)
            except (OSError, AttributeError):
                job.process.terminate()
            try:
                job.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(job.process.pid, signal.SIGKILL)
                except (OSError, AttributeError):
                    job.process.kill()
                job.process.wait(timeout=2)
            self._jobs.pop(name, None)
            return {"ok": True}

    def tail(self, name: str, lines: int = 120) -> str:
        if name != "mcbuild-server":
            return ""
        path = self.log_dir / "mcbuild-server.log"
        try:
            content = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return ""
        return "\n".join(content[-max(1, min(lines, 500)) :])


JOBS = JobManager()


def _status_snapshot() -> dict[str, Any]:
    return {
        "timestamp": time.time(),
        "host": {
            "hostname": platform.node(),
            "platform": platform.platform(),
            "python": platform.python_version(),
            "wsl": "microsoft" in platform.release().lower() or "WSL_DISTRO_NAME" in os.environ,
            "wsl_distro": os.getenv("WSL_DISTRO_NAME"),
            "train_python": _detect_train_python(),
        },
        "cpu": _cpu_snapshot(),
        "memory": _memory_snapshot(),
        "disks": _disk_snapshot(),
        "gpu": _gpu_snapshot(),
        "jobs": JOBS.status(),
    }


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "GabConDashboard/0.1"

    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write("[dashboard] " + (fmt % args) + "\n")

    def _json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _html(self) -> None:
        body = DASHBOARD_HTML.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:")
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(body)

    def _read_payload(self) -> dict[str, Any]:
        try:
            length = min(int(self.headers.get("Content-Length", "0")), 16_384)
        except ValueError:
            length = 0
        if not length:
            return {}
        try:
            data = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._html()
            return
        if path == "/api/status":
            self._json(_status_snapshot())
            return
        if path == "/api/jobs/mcbuild-server/log":
            self._json({"log": JOBS.tail("mcbuild-server")})
            return
        self._json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path.startswith("/api/diagnostics/"):
            name = path.rsplit("/", 1)[-1]
            result = _diagnostic(name)
            self._json(result, HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_REQUEST)
            return
        if path == "/api/jobs/mcbuild-server/start":
            result = JOBS.start_mcbuild_server(self._read_payload())
            self._json(result, HTTPStatus.OK if result.get("ok") else HTTPStatus.CONFLICT)
            return
        if path == "/api/jobs/mcbuild-server/stop":
            result = JOBS.stop("mcbuild-server")
            self._json(result, HTTPStatus.OK if result.get("ok") else HTTPStatus.CONFLICT)
            return
        self._json({"error": "Not found"}, HTTPStatus.NOT_FOUND)


def main() -> None:
    parser = argparse.ArgumentParser(description="GabCon local dual-GPU workstation dashboard.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address; keep loopback unless you add your own network controls.")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    server = ThreadingHTTPServer((args.host, args.port), DashboardHandler)
    print(f"GabCon Rig Control listening on http://{args.host}:{args.port}")
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        print("WARNING: dashboard is not authenticated; bind to loopback for normal use.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
