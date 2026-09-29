# ruff: noqa: E501
"""Embedded frontend for the GabCon workstation dashboard."""

DASHBOARD_HTML = r"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GabCon Rig Control</title>
<style>
:root{color-scheme:dark;--bg:#07110f;--card:#0d1b18;--card2:#10231e;--line:#244038;--text:#eef7f4;--muted:#8fa8a0;--green:#60f6b0;--cyan:#61d8ff;--amber:#ffc66d;--red:#ff6f7d}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 80% -10%,#14372c 0,transparent 30%),var(--bg);font:14px/1.45 Inter,system-ui,sans-serif;color:var(--text)}
button,input,select{font:inherit}.wrap{max-width:1440px;margin:auto;padding:24px}.top{display:flex;justify-content:space-between;gap:16px;align-items:center;margin-bottom:20px}
.brand{display:flex;gap:12px;align-items:center}.logo{width:42px;height:42px;border-radius:12px;border:1px solid #3a725e;background:#10251f;display:grid;place-items:center;color:var(--green);font-weight:900}.title{font-size:20px;font-weight:800}.muted{color:var(--muted);font-size:12px}
.live,.chip{border:1px solid var(--line);border-radius:999px;background:#0c1916;padding:6px 10px;color:var(--muted);font-size:11px}.dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 10px var(--green);margin-right:7px}
.grid{display:grid;gap:14px}.summary{grid-template-columns:repeat(4,minmax(0,1fr));margin-bottom:14px}.two{grid-template-columns:repeat(2,minmax(0,1fr));margin-bottom:14px}.card{background:linear-gradient(180deg,#0e1e1a,#0b1714);border:1px solid var(--line);border-radius:15px;padding:16px;box-shadow:0 12px 40px #0004}
.k{font-size:10px;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);font-weight:800}.big{font-size:26px;font-weight:800;margin:5px 0}.bar{height:7px;border-radius:999px;background:#172c27;overflow:hidden;margin-top:10px}.fill{height:100%;background:linear-gradient(90deg,var(--green),var(--cyan));width:0;transition:width .3s}
.head{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:11px}.head h2{font-size:14px;margin:0}.gpu-title{font-size:16px;font-weight:800}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:13px}.stat{padding:10px;border:1px solid #1d3931;border-radius:10px;background:#10201c}.stat b{display:block;font-size:16px;margin-top:3px}
.good{color:var(--green)}.warn{color:var(--amber)}.bad{color:var(--red)}.strategy{display:grid;grid-template-columns:1.15fr 1fr 1fr;gap:9px}.route{padding:12px;border:1px solid #23463b;border-radius:11px;background:#0f211c}.route.best{border-color:#3b8b6e}.route strong{display:block;margin-bottom:4px}
.flow{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}.step{padding:5px 8px;border:1px solid #23443a;border-radius:7px;background:#122720;color:#b9ccc6}.disks{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.disk{padding:10px;border:1px solid #1d3a31;border-radius:9px;background:#0f201b}
.form{display:grid;grid-template-columns:2fr .7fr .8fr .8fr;gap:8px;margin:10px 0}.field label{display:block;color:var(--muted);font-size:10px;text-transform:uppercase;margin-bottom:4px}.field input,.field select{width:100%;padding:8px;border-radius:8px;border:1px solid #28473e;background:#091511;color:var(--text)}
.actions{display:flex;gap:8px;flex-wrap:wrap}.btn{cursor:pointer;padding:8px 11px;border:1px solid #315a4e;border-radius:9px;background:#122720;color:#d9ece6}.btn:hover{border-color:#60f6b080}.btn.primary{background:#174c3b;border-color:#3cae83}.btn.danger{background:#2b171b;border-color:#673844;color:#ffb7bf}
.term{min-height:190px;max-height:360px;overflow:auto;white-space:pre-wrap;margin-top:10px;padding:12px;border-radius:10px;border:1px solid #1a302a;background:#050a09;color:#b7d8ce;font:12px/1.55 ui-monospace,monospace}.cmd{padding:9px 10px;border:1px solid #213c34;border-radius:8px;background:#07110e;color:#a9c7be;font:11px/1.5 ui-monospace,monospace;overflow:auto}
.copyrow{display:flex;gap:8px;margin-top:10px}.copyrow .cmd{flex:1}.footer{text-align:center;color:#617970;font-size:11px;margin-top:18px}
@media(max-width:980px){.summary,.two{grid-template-columns:1fr 1fr}.strategy{grid-template-columns:1fr}.form{grid-template-columns:1fr 1fr}.stats{grid-template-columns:1fr 1fr}}
@media(max-width:620px){.wrap{padding:14px}.summary,.two,.stats,.disks,.form{grid-template-columns:1fr}.live{display:none}}
</style>
</head>
<body><main class="wrap">
<header class="top"><div class="brand"><div class="logo">G</div><div><div class="title">GabCon Rig Control</div><div class="muted" id="host">Connexion…</div></div></div><div class="live"><span class="dot"></span><span id="updated">local</span></div></header>

<section class="grid summary">
<div class="card"><div class="k">CPU</div><div class="big" id="cpu">—</div><div class="muted" id="load">load —</div><div class="bar"><div class="fill" id="cpuBar"></div></div></div>
<div class="card"><div class="k">RAM</div><div class="big" id="ram">—</div><div class="muted" id="ramDetail">—</div><div class="bar"><div class="fill" id="ramBar"></div></div></div>
<div class="card"><div class="k">GPU</div><div class="big" id="gpuCount">—</div><div class="muted" id="driver">driver —</div><div class="bar"><div class="fill" id="gpuBar"></div></div></div>
<div class="card"><div class="k">Uptime WSL</div><div class="big" id="uptime">—</div><div class="muted" id="distro">—</div></div>
</section>

<div class="head"><h2>Accélérateurs NVIDIA</h2><span class="chip">refresh 2s</span></div>
<section class="grid two" id="gpuGrid"><div class="card">Détection GPU…</div></section>

<section class="grid two">
<div class="card"><div class="head"><h2>Profil de charge</h2><span class="chip good">recommandé</span></div>
<div class="strategy"><div class="route best"><strong>GPU 0 · Train / QLoRA</strong><span class="muted">Premier smoke-test Qwen en 4-bit.</span></div><div class="route"><strong>GPU 1 · Workers</strong><span class="muted">Rendu, Minecraft, tâches auxiliaires.</span></div><div class="route"><strong>2× GPU · Plus tard</strong><span class="muted">DDP / ZeRO / FSDP après mesure PCIe.</span></div></div>
<div class="flow"><span class="step">CUDA</span><span class="step">PyTorch</span><span class="step">bitsandbytes</span><span class="step">Qwen3.5</span><span class="step">QLoRA</span><span class="step">optimisations</span></div>
<div class="copyrow"><div class="cmd" id="gpu0cmd">export CUDA_VISIBLE_DEVICES=0</div><button class="btn" onclick="copyText('gpu0cmd')">Copier</button></div></div>
<div class="card"><div class="head"><h2>Stockage</h2><span class="chip">WSL / Windows</span></div><div class="disks" id="disks"></div><p class="muted">Le training reste dans le filesystem Linux WSL sur D:. C: reste visible pour éviter que caches et modèles le remplissent.</p></div>
</section>

<section class="grid two">
<div class="card"><div class="head"><h2>Service GabCon</h2><span class="chip" id="jobStatus">arrêté</span></div>
<div class="form"><div class="field"><label>Model</label><input id="model" value="anthropic/claude-sonnet-5"></div><div class="field"><label>Iterations</label><input id="iters" type="number" min="1" max="30" value="6"></div><div class="field"><label>Reasoning</label><select id="reasoning"><option>off</option><option>low</option><option>medium</option><option>high</option></select></div><div class="field"><label>GPU</label><select id="affinity"><option value="">auto</option><option value="0">GPU 0</option><option value="1">GPU 1</option><option value="0,1">0 + 1</option></select></div></div>
<div class="actions"><button class="btn primary" onclick="startServer()">Démarrer mcbuild-server</button><button class="btn danger" onclick="stopServer()">Arrêter</button><button class="btn" onclick="loadLog()">Logs</button></div><div class="term" id="serviceLog">Aucun service lancé depuis ce dashboard.</div></div>
<div class="card"><div class="head"><h2>Diagnostics machine</h2><span class="chip">allow-list</span></div>
<div class="actions"><button class="btn" onclick="diag('nvidia')">nvidia-smi</button><button class="btn" onclick="diag('topology')">Topologie PCIe</button><button class="btn" onclick="diag('pcie')">PCIe width/gen</button><button class="btn" onclick="diag('pytorch')">PyTorch / CUDA</button><button class="btn" onclick="diag('bitsandbytes')">bitsandbytes</button><button class="btn" onclick="diag('swift')">ms-swift</button></div>
<div class="term" id="terminal">Choisis un diagnostic. Aucune commande libre n'est exposée par l'API.</div></div>
</section>

<section class="card"><div class="head"><h2>Smoke-test Qwen3.5-4B</h2><span class="chip">manuel</span></div><p class="muted">Commande préparée pour le premier essai 4-bit sur GPU 0. Elle est volontairement copy-only.</p><div class="copyrow"><div class="cmd" id="qwen">export CUDA_VISIBLE_DEVICES=0; export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True; swift infer --model Qwen/Qwen3.5-4B --use_hf true --infer_backend transformers --quant_method bnb --quant_bits 4 --torch_dtype bfloat16 --enable_thinking false --max_new_tokens 128</div><button class="btn" onclick="copyText('qwen')">Copier</button></div></section>
<div class="footer">GabCon BuildAI · dashboard local non authentifié · bind 127.0.0.1 recommandé</div>
</main>
<script>
const $=id=>document.getElementById(id);
const fmt=n=>{if(n==null)return'—';const u=['B','KiB','MiB','GiB','TiB'];let i=0,v=n;while(v>=1024&&i<u.length-1){v/=1024;i++}return v.toFixed(i>1?1:0)+' '+u[i]};
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const up=s=>{if(s==null)return'—';const h=Math.floor(s/3600),d=Math.floor(h/24);return d?d+'j '+h%24+'h':h+'h '+Math.floor(s%3600/60)+'m'};
async function api(path,opt){const r=await fetch(path,opt);const j=await r.json();if(!r.ok)throw new Error(j.error||j.stderr||('HTTP '+r.status));return j}
function gpuCard(g){const used=Number(g['memory.used']||0),total=Number(g['memory.total']||0),util=Number(g['utilization.gpu']||0),temp=Number(g['temperature.gpu']||0),vr=total?Math.min(100,used/total*100):0;return '<div class="card"><div class="head"><div><div class="gpu-title">GPU '+esc(g.index)+' · '+esc(g.name)+'</div><div class="muted">PCIe Gen '+esc(g['pcie.link.gen.current']??'?')+' ×'+esc(g['pcie.link.width.current']??'?')+' · '+esc(g['clocks.current.graphics']??'—')+' MHz</div></div><span class="chip '+(temp>=80?'bad':temp>=70?'warn':'good')+'">'+(temp||'—')+'°C</span></div><div class="stats"><div class="stat"><span class="muted">GPU LOAD</span><b>'+util+'%</b></div><div class="stat"><span class="muted">VRAM</span><b>'+used+' / '+total+' MiB</b></div><div class="stat"><span class="muted">POWER</span><b>'+esc(g['power.draw']??'—')+' W</b></div><div class="stat"><span class="muted">MEM LOAD</span><b>'+esc(g['utilization.memory']??'—')+'%</b></div></div><div class="bar"><div class="fill" style="width:'+vr+'%"></div></div></div>'}
async function refresh(){try{const s=await api('/api/status');$('host').textContent=(s.host.hostname||'workstation')+' · '+(s.host.wsl_distro||s.host.platform);$('updated').textContent='live · '+new Date().toLocaleTimeString();$('cpu').textContent=(s.cpu.logical_cpus??'—')+' threads';$('load').textContent='load '+(s.cpu.load_average?s.cpu.load_average[0]:'—');$('cpuBar').style.width=Math.min(100,(s.cpu.load_average?.[0]||0)/(s.cpu.logical_cpus||1)*100)+'%';$('ram').textContent=(s.memory.used_percent??'—')+'%';$('ramDetail').textContent=fmt(s.memory.used_bytes)+' / '+fmt(s.memory.total_bytes);$('ramBar').style.width=(s.memory.used_percent||0)+'%';$('uptime').textContent=up(s.cpu.uptime_seconds);$('distro').textContent=s.host.wsl_distro||'Linux';const gs=s.gpu.gpus||[];$('gpuCount').textContent=gs.length+' × GPU';$('driver').textContent=gs[0]?'driver '+gs[0].driver_version:(s.gpu.error||'indisponible');$('gpuBar').style.width=(gs.length?Math.max(...gs.map(g=>Number(g['utilization.gpu']||0))):0)+'%';$('gpuGrid').innerHTML=gs.length?gs.map(gpuCard).join(''):'<div class="card"><span class="bad">NVIDIA indisponible</span><div class="muted">'+esc(s.gpu.error)+'</div></div>';$('disks').innerHTML=(s.disks||[]).map(d=>'<div class="disk"><strong>'+esc(d.label)+'</strong><div class="muted">'+fmt(d.free_bytes)+' libres</div><div class="bar"><div class="fill" style="width:'+(d.used_percent||0)+'%"></div></div></div>').join('');const job=(s.jobs||[]).find(j=>j.name==='mcbuild-server');$('jobStatus').textContent=job?'PID '+job.pid:'arrêté';$('jobStatus').className='chip '+(job?'good':'')}catch(e){$('updated').textContent='hors ligne'}}
async function diag(name){$('terminal').textContent='$ '+name+'…';try{const r=await api('/api/diagnostics/'+name,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});$('terminal').textContent='$ '+r.command.join(' ')+'\n\n'+(r.stdout||'')+(r.stderr?'\n'+r.stderr:'')+'\n\n['+(r.duration_ms??'?')+' ms]'}catch(e){$('terminal').textContent='Erreur: '+e.message}}
async function startServer(){const body={model:$('model').value,max_iters:Number($('iters').value),reasoning:$('reasoning').value,gpu:$('affinity').value};try{const r=await api('/api/jobs/mcbuild-server/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});$('serviceLog').textContent='Démarré PID '+r.pid+'\n'+r.command.join(' ');refresh()}catch(e){$('serviceLog').textContent='Erreur: '+e.message}}
async function stopServer(){try{await api('/api/jobs/mcbuild-server/stop',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});$('serviceLog').textContent='mcbuild-server arrêté.';refresh()}catch(e){$('serviceLog').textContent='Erreur: '+e.message}}
async function loadLog(){try{const r=await api('/api/jobs/mcbuild-server/log');$('serviceLog').textContent=r.log||'Log vide.';$('serviceLog').scrollTop=$('serviceLog').scrollHeight}catch(e){$('serviceLog').textContent=e.message}}
async function copyText(id){try{await navigator.clipboard.writeText($(id).textContent)}catch(e){}}
refresh();setInterval(refresh,2000);setInterval(()=>{if($('jobStatus').textContent!=='arrêté')loadLog()},5000);
</script>
</body></html>
"""
