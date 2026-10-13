'use strict';

// ChatGPT creates the requested file directly. Prompt preparation needs no Studio build step.
// The existing local preview and converters below remain optional.
const $ = id => document.getElementById(id);
const els = {
  code: $('code'), idea: $('idea'), seed: $('seed'), canvas: $('voxelCanvas'),
  image: $('renderImage'), viewport: $('viewport'), toast: $('toast'),
  build: $('buildBtn'), lineNumbers: $('lineNumbers'), history: $('historyGrid')
};
let current = null, model = null, mode = '3d', busy = false, toastTimer = 0;
let studioBlockLimit = 1_000_000;
let deferredInstallPrompt = null;
const cam = { yaw: Math.PI / 4, elev: 0.56, zoom: 1, px: 0, py: 0 };
const SAMPLE = [
  '# GabCon-BuildAI : tour médiévale',
  'fill(-7, 0, -7, 7, 0, 7, "cobblestone")',
  'cylinder(0, 0, 1, 17, 5, "stone_bricks", hollow=True)',
  'for y in range(1, 17):',
  '    for x, z in [(-4,-4),(-4,4),(4,-4),(4,4)]:',
  '        set_block(x, y, z, "polished_andesite")',
  'fill(-1, 1, -5, 1, 3, -5, "air")',
  'for y in [7, 12]:',
  '    for x, z in [(0,-5),(0,5),(-5,0),(5,0)]:',
  '        set_block(x, y, z, "glass_pane")',
  'cylinder(0, 0, 18, 1, 7, "spruce_planks")',
  'cylinder(0, 0, 19, 1, 6, "spruce_planks")',
  'cylinder(0, 0, 20, 1, 5, "spruce_planks")',
  'cylinder(0, 0, 21, 1, 4, "dark_oak_planks")',
  'cylinder(0, 0, 22, 1, 3, "dark_oak_planks")',
  'cylinder(0, 0, 23, 1, 2, "dark_oak_planks")',
  'set_block(0, 24, 0, "lightning_rod")'
].join('\n');

function notify(message, isError) {
  els.toast.textContent = message;
  els.toast.classList.toggle('error', !!isError);
  els.toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => els.toast.classList.remove('show'), isError ? 6500 : 3500);
}
function status(message, kind) {
  $('statusText').textContent = message;
  $('statusChip').classList.remove('ready', 'error');
  if (kind) $('statusChip').classList.add(kind);
}
function loading(active) {
  if (active) $('buildError').classList.add('hidden');
  busy = active;
  els.build.disabled = active;
  $('buildBtnText').textContent = active ? 'Construction en cours...' : 'Visualiser la construction';
  $('buildBtnIcon').textContent = active ? '◌' : '◩';
  $('processing').classList.toggle('hidden', !active);
  if (active) status('GÉNÉRATION...');
}
function extractCode(s) { return GabConPrompt.extractBlueprint(s); }
function currentBrief() {
  return GabConPrompt.createBrief({
    idea:els.idea.value, style:$('briefStyle').value,
    size:$('briefSize').value, detail:$('briefDetail').value,
    blockLimit:studioBlockLimit, fileFormat:$('outputFormat').value
  });
}
function downloadBrief() {
  const brief = JSON.stringify(currentBrief(), null, 2) + '\n';
  const blob = new Blob([brief], {type:'application/json;charset=utf-8'});
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href=url;link.download='gabcon-construction-brief.json';
  document.body.appendChild(link);link.click();link.remove();
  setTimeout(()=>URL.revokeObjectURL(url),30000);
  notify('Cahier des charges JSON sauvegardé. Le format de sortie sélectionné y est inclus.');
}
function refreshEditor() {
  const lines = els.code.value.split('\n').length;
  els.lineNumbers.textContent = Array.from({ length: lines }, (_, n) => n + 1).join('\n');
  $('codeCount').textContent = lines + (lines > 1 ? ' lignes' : ' ligne');
  try { localStorage.setItem('gabcon-code', els.code.value); } catch (_) {}
}
function blueprintPrompt() { return GabConPrompt.buildPrompt(currentBrief()); }
function outputFormat() { return GabConPrompt.formatFor($('outputFormat').value); }
function updateOutputFormat() {
  const format=outputFormat(),info=GabConPrompt.getFormat(format);
  $('formatTitle').textContent=info.name;
  $('formatPros').textContent=info.good;
  $('formatCons').textContent=info.bad;
  $('formatWorkflow').textContent=info.workflow;
  $('briefFlow').textContent=info.workflow;
  $('editorLanguage').textContent=info.language.toUpperCase()+' / '+info.extension.toUpperCase();
  $('buildBtnText').textContent=GabConFormats.canExecute(format)?'Aperçu local facultatif':'Aperçu local indisponible';
  els.build.disabled=!GabConFormats.canExecute(format);
  els.build.title=info.executable?'Exécuter avec le moteur BuildAI local':'Télécharge le fichier : ce format ne s’exécute pas dans Studio';
  $('downloadResponse').textContent=format==='auto'?'⇩ Téléchargement dans ChatGPT':'⇩ Sauvegarder '+GabConFormats.downloadName(format)+' (texte)';
  $('downloadResponse').disabled=format==='auto';
  $('downloadResponse').title=format==='auto'?'Le type de fichier est déterminé par ChatGPT : télécharge-le depuis la conversation.':'Sauvegarder le texte localement si besoin';
  $('copyRepair').classList.toggle('hidden',format==='mcfunction'||format==='md');
  try { localStorage.setItem('gabcon-output-format-direct-v1',format); } catch (_) {}
}
function downloadResponse() {
  const format=outputFormat();
  if (format==='auto') return notify('Télécharge le fichier directement dans ChatGPT, qui en choisit le format.',true);
  let body=GabConFormats.textForFormat(els.code.value,format);
  if (!body.trim()) return notify('Colle d’abord la réponse de ChatGPT dans l’éditeur.',true);
  if (format==='json') {
    try { GabConFormats.compileJsonOps(body); }
    catch(err) { return notify('JSON invalide : '+err.message,true); }
  }
  const type=format==='json'?'application/json':'text/plain';
  const blob=new Blob([body],{type:type+';charset=utf-8'});
  const url=URL.createObjectURL(blob),link=document.createElement('a');
  link.href=url;link.download=GabConFormats.downloadName(format);
  document.body.appendChild(link);link.click();link.remove();
  setTimeout(()=>URL.revokeObjectURL(url),30000);
  notify(format==='schem'?'Blueprint Python sauvegardé. Pour obtenir final.schem, clique sur Visualiser.':'Fichier '+link.download+' sauvegardé.');
}

async function copyForChatGPT(value, successMessage) {
  try {
    await navigator.clipboard.writeText(value);
    notify(successMessage);
  } catch (_) {
    const temp = document.createElement('textarea');
    temp.value = value;
    temp.style.cssText = 'position:fixed;left:-10000px';
    document.body.appendChild(temp);temp.select();
    const ok=document.execCommand('copy');
    temp.remove();
    notify(ok ? successMessage : 'La copie automatique est indisponible.', !ok);
  }
}
async function copyPrompt() {
  const info=GabConPrompt.getFormat(outputFormat());
  await copyForChatGPT(blueprintPrompt(), 'Prompt copié pour ChatGPT : '+info.name+'. Demande-lui le fichier téléchargeable.');
}
async function copyRepair() {
  const message=$('buildErrorText').textContent.trim();
  if(!message) return notify('Aucune erreur à corriger.',true);
  const code=extractCode(els.code.value);
  if(!code.trim()) return notify('Aucun Python à corriger.',true);
  try {
    const prompt=outputFormat()==='json'
      ? GabConPrompt.repairJsonPrompt(currentBrief(),els.code.value,message)
      : GabConPrompt.repairPrompt(currentBrief(),code,message);
    await copyForChatGPT(prompt, 'Demande de correction copiée ! ChatGPT pourra renvoyer blueprint.py complet.');
  } catch (err) { notify(err.message || 'Impossible de préparer la correction.', true); }
}
async function installApp() {
  if (window.matchMedia('(display-mode: standalone)').matches || navigator.standalone) {
    return notify("GabCon Studio est déjà ouvert comme application.");
  }
  if (deferredInstallPrompt) {
    const event = deferredInstallPrompt;
    deferredInstallPrompt = null;
    event.prompt();
    try { await event.userChoice; } catch (_) {}
    return;
  }
  if (/iPhone|iPad|iPod/i.test(navigator.userAgent)) {
    return notify("iPhone / iPad : ouvre ce site avec Safari, touche Partager, puis « Sur l'écran d’accueil ».");
  }
  notify("Dans le menu de ton navigateur, choisis « Installer l’application » ou « Ajouter à l’écran d’accueil ». Utilise une adresse HTTPS.");
}
function registerMobileApp() {
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    deferredInstallPrompt = event;
  });
  if ('serviceWorker' in navigator && window.isSecureContext) {
    window.addEventListener('load', () =>
      navigator.serviceWorker.register('/sw.js').catch(err => console.debug('PWA unavailable', err))
    );
  }
}
function numberText(num) { return Number(num || 0).toLocaleString('fr-FR'); }
function colorFor(name) {
  name = String(name || '').toLowerCase();
  if (/stone|cobble|andesite|tuff|deepslate/.test(name)) return '#929d95';
  if (/spruce|dark_oak/.test(name)) return '#81624a';
  if (/wood|planks|oak/.test(name)) return '#b2966b';
  if (/glass/.test(name)) return '#86a9b4';
  if (/brick|terracotta/.test(name)) return '#a97965';
  if (/grass|leaf|leaves/.test(name)) return '#729c77';
  if (/copper/.test(name)) return '#bd865c';
  let hash = 0;
  for (const ch of name) hash = (Math.imul(hash, 31) + ch.charCodeAt(0)) | 0;
  return 'hsl(' + Math.abs(hash % 360) + ',22%,58%)';
}
function updateMaterials(materials, total) {
  const bar = $('materialBar'), list = $('materialList');
  bar.replaceChildren(); list.replaceChildren();
  if (!Array.isArray(materials) || !materials.length) return;
  let covered = 0;
  for (const pair of materials.slice(0, 6)) {
    const name = pair[0], count = Number(pair[1]) || 0;
    covered += count;
    const segment = document.createElement('div');
    segment.style.width = 100 * count / Math.max(1, total) + '%';
    segment.style.background = colorFor(name);
    segment.title = name + ' : ' + numberText(count);
    bar.appendChild(segment);
    const item = document.createElement('span');
    item.className = 'material-item';
    const sw = document.createElement('span');
    sw.className = 'material-swatch';
    sw.style.background = colorFor(name);
    const label = document.createElement('span');
    label.textContent = name.split(':').pop() + ' (' + numberText(count) + ')';
    item.append(sw, label);
    list.appendChild(item);
  }
  if (total > covered) {
    const rest = document.createElement('div');
    rest.style.width = 100 * (total - covered) / total + '%';
    rest.style.background = '#4c6053';
    bar.appendChild(rest);
  }
  $('paletteHint').textContent = 'Principaux matériaux';
}
function downloads(urls) {
  for (const [id, key] of [['downloadSchem','schem'],['downloadPy','blueprint'],['downloadRender','render'],['downloadStats','stats']]) {
    const node = $(id), href = urls && urls[key];
    node.classList.toggle('disabled', !href);
    node.setAttribute('aria-disabled', String(!href));
    if (href) {
      node.href = href; node.setAttribute('download', '');
      node.removeAttribute('tabindex');
    } else {
      node.removeAttribute('href'); node.setAttribute('tabindex', '-1');
    }
  }
}
function viewMode(next) {
  if (next === 'render' && !current) return notify('Génère une construction pour voir son rendu.');
  if (next === '3d' && !model && current) return notify('Vue 3D désactivée pour ce projet.', true);
  mode = next;
  $('view3d').classList.toggle('selected', next === '3d');
  $('viewRender').classList.toggle('selected', next === 'render');
  els.canvas.classList.toggle('hidden', next !== '3d');
  els.image.classList.toggle('hidden', next !== 'render');
  $('dragHint').classList.toggle('hidden', next !== '3d');
  document.querySelector('.camera-actions').classList.toggle('hidden', next !== '3d');
  $('previewMode').textContent = next === '3d' ? 'APERÇU SIMPLIFIÉ' : 'RENDU BUILD AI';
  if (next === '3d') requestDraw();
}
async function openBuild(item) {
  current = item;
  const stats = item.stats || {};
  $('statBlocks').textContent = numberText(stats.block_count);
  $('statDims').textContent = Array.isArray(stats.dims) ? stats.dims.join(' × ') : '—';
  $('statMaterials').textContent = String(stats.material_count || stats.top_materials?.length || '—');
  const timings = stats.timings_ms;
  const timingLabels = [['blueprint','Python'],['validation','Validation'],['render','Rendu'],['schematic','.schem'],['browser_preview','3D']];
  $('timingInfo').textContent = timings
    ? timingLabels.filter(([key]) => Number.isFinite(timings[key]))
      .map(([key, label]) => label + ' ' + (timings[key] / 1000).toFixed(2) + ' s').join(' · ')
    : 'Mesures indisponibles pour cette ancienne construction.';
  $('previewSubtitle').textContent = item.name;
  $('previewMode').textContent = {fast:'RAPIDE · SANS OMBRES',quality:'QUALITÉ · 6 VUES',top_down:'GRAND BUILD · TOP'}[stats.preview_mode] || 'APERÇU SIMPLIFIÉ';
  $('exportBadge').textContent = 'FICHIERS PRÊTS';
  $('exportBadge').classList.add('ready');
  $('viewLabel').textContent = 'GABCON BUILD / ' + item.id.slice(0, 15).toUpperCase();
  status('CONSTRUCTION PRÊTE', 'ready');
  updateMaterials(stats.top_materials, stats.block_count || 0);
  downloads(item.urls);
  els.image.src = item.urls.render;
  model = null;
  try {
    const r = await fetch(item.urls.voxels);
    if (!r.ok) throw Error('Aperçu indisponible');
    const data = await r.json();
    if (data.too_large || !data.surface?.length) {
      viewMode('render');
      notify('Construction volumineuse : aperçu PNG allégé. Le schematic contient tous les blocs.');
    } else {
      model = { voxels: data.surface, dims: stats.dims || [16, 16, 16] };
      resetCamera();
      viewMode('3d');
    }
  } catch (_) { viewMode('render'); }
  if (stats.palette_warnings?.length) notify('Vérifie les avertissements de palette dans stats.json.');
}
async function build() {
  if (busy) return;
  const format=outputFormat();
  if (!GabConFormats.canExecute(format)) return notify('Ce format ne s’exécute pas ici. Télécharge le fichier texte.',true);
  let source;
  try { source=GabConFormats.contentForBuild(els.code.value,format); }
  catch(err) {
    $('buildErrorText').textContent=err.message||'Fichier invalide.';
    $('buildError').classList.remove('hidden');
    return notify('Le format demandé comporte une erreur.',true);
  }
  if (!source.trim()) return notify('Colle d’abord la réponse de ChatGPT.', true);
  const seed = Number(els.seed.value);
  if (!Number.isInteger(seed) || seed < 0 || seed > 2147483647) return notify('Seed invalide.', true);
  if (format!=='json' && source !== els.code.value) { els.code.value = source; refreshEditor(); }
  loading(true);
  try {
    const response = await fetch('/api/build', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({source, name:els.idea.value.trim() || 'Construction', seed, preview_mode:$('renderMode').value})
    });
    const data = await response.json();
    if (!response.ok) throw Error(data.error || 'Erreur du moteur BuildAI');
    await openBuild(data);
    await refreshHistory();
    ['step1','step2','step3','step4'].forEach((id, i) => $(id).classList.toggle('current', i === 3));
    notify('Construction prête ! Explore le rendu et exporte ton schematic.');
  } catch (err) {
    console.error(err);
    status('ERREUR', 'error');
    $('buildErrorText').textContent = err.message || 'Erreur inconnue';
    $('buildError').classList.remove('hidden');
    notify('Échec de la génération : consulte le message sous l’éditeur.', true);
  } finally { loading(false); }
}
async function refreshHistory() {
  let items = [];
  try { const r = await fetch('/api/builds'); if (r.ok) items = await r.json(); } catch (_) {}
  els.history.replaceChildren();
  if (!items.length) {
    const empty = document.createElement('div'); empty.className='history-empty';
    empty.innerHTML='<span>▧</span><strong>Ton atelier est prêt.</strong><p>Ta première création apparaîtra ici.</p>';
    els.history.appendChild(empty); return;
  }
  for (const item of items.slice(0, 9)) {
    const card = document.createElement('button'); card.className='history-card';
    const wrap = document.createElement('div'); wrap.className='history-thumb';
    const img = document.createElement('img'); img.loading='lazy'; img.alt='Aperçu'; img.src=item.urls.render;
    wrap.appendChild(img);
    const det = document.createElement('div'); det.className='history-details';
    const name = document.createElement('b'); name.textContent=item.name;
    const desc = document.createElement('small');
    desc.textContent=numberText(item.stats.block_count)+' blocs · '+new Date(item.created_at).toLocaleDateString('fr-FR');
    det.append(name, desc); card.append(wrap, det);
    card.addEventListener('click', async () => {
      try {
        await openBuild(item);
        $('outputFormat').value='py';updateOutputFormat();
        els.code.value = await (await fetch(item.urls.blueprint)).text();
        els.idea.value = item.name;
        refreshEditor();
        $('editor').scrollIntoView({behavior:'smooth'});
      } catch (_) { notify('Impossible de charger ce projet.', true); }
    });
    els.history.appendChild(card);
  }
}
async function health() {
  try {
    const r = await fetch('/api/health');
    const data = await r.json();
    if (!data.project_detected) throw Error('Dossier mcbuild introuvable');
    studioBlockLimit = Number(data.studio_max_blocks) || 1_000_000;
    $('onlineDot').classList.add('good'); $('onlineLabel').textContent='Moteur local disponible';
  } catch (_) { $('onlineDot').classList.add('bad'); $('onlineLabel').textContent='Moteur indisponible'; }
}

// 3D canvas renderer: visible block faces, painter's algorithm, no JS dependencies.
const FACES = [
  { bit:1, normal:[1,0,0], shade:.78, pts:[[1,0,0],[1,0,1],[1,1,1],[1,1,0]] },
  { bit:2, normal:[-1,0,0], shade:.70, pts:[[0,0,0],[0,1,0],[0,1,1],[0,0,1]] },
  { bit:4, normal:[0,1,0], shade:1.08, pts:[[0,1,0],[1,1,0],[1,1,1],[0,1,1]] },
  { bit:8, normal:[0,-1,0], shade:.48, pts:[[0,0,0],[0,0,1],[1,0,1],[1,0,0]] },
  { bit:16, normal:[0,0,1], shade:.87, pts:[[0,0,1],[0,1,1],[1,1,1],[1,0,1]] },
  { bit:32, normal:[0,0,-1], shade:.63, pts:[[0,0,0],[1,0,0],[1,1,0],[0,1,0]] }
];
function demoModel() {
  const blocks = new Map();
  function put(x,y,z,r,g,b) { blocks.set([x,y,z].join(','), [x,y,z,r,g,b]); }
  for(let x=0;x<15;x++) for(let z=0;z<15;z++) put(x,0,z,100,124,93);
  for(let y=1;y<17;y++) for(let x=3;x<=11;x++) for(let z=3;z<=11;z++)
    if(x===3 || x===11 || z===3 || z===11) put(x,y,z,144,150,142);
  for(let y=1;y<16;y++) for(const x of [3,11]) for(const z of [3,11]) put(x,y,z,107,110,104);
  for(let y=1;y<=3;y++) for(let x=6;x<=8;x++) put(x,y,3,30,40,38);
  for(const y of [8,12]) for(let x=6;x<=8;x++) {put(x,y,3,83,133,151);put(x,y,11,83,133,151);}
  for(let y=17;y<=21;y++) {
    const radius=23-y;
    for(let x=7-radius;x<=7+radius;x++) for(let z=7-radius;z<=7+radius;z++)
      if(Math.abs(x-7)===radius || Math.abs(z-7)===radius) put(x,y,z,96,69,49);
  }
  put(7,22,7,176,164,123); put(7,23,7,176,164,123);
  const neigh=[[1,0,0],[-1,0,0],[0,1,0],[0,-1,0],[0,0,1],[0,0,-1]];
  const surface=[];
  for(const b of blocks.values()) {
    let mask=0;
    neigh.forEach((d,i) => {
      if(!blocks.has([b[0]+d[0],b[1]+d[1],b[2]+d[2]].join(','))) mask|=1<<i;
    });
    if(mask) surface.push([...b,mask]);
  }
  return { voxels:surface,dims:[15,24,15] };
}
const DEMO = demoModel();
let queued=false;
function requestDraw() {
  if(queued) return;
  queued=true;
  requestAnimationFrame(() => { queued=false; draw(); });
}
function shade(rgb,factor) {
  return 'rgb('+rgb.map(c=>Math.round(Math.max(0,Math.min(255,c*factor)))).join(',')+')';
}
function draw() {
  if(mode!=='3d') return;
  const rect=els.canvas.getBoundingClientRect(), w=rect.width, h=rect.height;
  if(w<20 || h<20) return;
  const dpr=Math.min(window.devicePixelRatio || 1,2);
  els.canvas.width=Math.round(w*dpr); els.canvas.height=Math.round(h*dpr);
  const ctx=els.canvas.getContext('2d');
  ctx.setTransform(dpr,0,0,dpr,0,0); ctx.clearRect(0,0,w,h);
  const data=model || DEMO, dims=data.dims, span=Math.max(dims[0],dims[2]);
  const scale=Math.min(22,w/(span*1.6+2),h/(dims[1]*1.3+span*.72+1))*cam.zoom;
  const sy=Math.sin(cam.yaw),cy=Math.cos(cam.yaw),se=Math.sin(cam.elev),ce=Math.cos(cam.elev);
  const vx=sy*ce,vy=se,vz=cy*ce, cx=dims[0]/2,cyy=dims[1]/2,cz=dims[2]/2;
  const project=(x,y,z)=>{
    const dx=x-cx,dy=y-cyy,dz=z-cz, horiz=dx*sy+dz*cy;
    return [w/2+cam.px+(dx*cy-dz*sy)*scale,h/2+cam.py+(-dy*ce+horiz*se)*scale,horiz*ce+dy*se];
  };
  ctx.strokeStyle='rgba(169,210,170,.07)'; ctx.lineWidth=1;
  const size=Math.ceil(span/2)+6;
  for(let i=-size;i<=size;i+=2){
    const a=project(cx-size,-.15,cz+i),b=project(cx+size,-.15,cz+i);
    const c=project(cx+i,-.15,cz-size),d=project(cx+i,-.15,cz+size);
    ctx.beginPath();ctx.moveTo(a[0],a[1]);ctx.lineTo(b[0],b[1]);ctx.stroke();
    ctx.beginPath();ctx.moveTo(c[0],c[1]);ctx.lineTo(d[0],d[1]);ctx.stroke();
  }
  const faces=FACES.filter(f=>f.normal[0]*vx+f.normal[1]*vy+f.normal[2]*vz>.02);
  const shapes=[];
  for(const v of data.voxels){
    const [x,y,z,r,g,b,mask]=v;
    for(const f of faces){
      if(!(mask & f.bit))continue;
      const pts=f.pts.map(p=>project(x+p[0],y+p[1],z+p[2]));
      shapes.push({pts, depth:pts.reduce((s,p)=>s+p[2],0)/4, fill:shade([r,g,b],f.shade)});
    }
  }
  shapes.sort((a,b)=>a.depth-b.depth);
  ctx.lineWidth=Math.max(.25,Math.min(.7,scale*.07));
  for(const s of shapes){
    ctx.beginPath();ctx.moveTo(s.pts[0][0],s.pts[0][1]);
    for(let i=1;i<4;i++)ctx.lineTo(s.pts[i][0],s.pts[i][1]);
    ctx.closePath();ctx.fillStyle=s.fill;ctx.fill();
    ctx.strokeStyle='rgba(12,19,18,.24)';ctx.stroke();
  }
  $('zoomValue').textContent=Math.round(cam.zoom*100)+'%';
}
function resetCamera() {
  Object.assign(cam,{yaw:Math.PI/4,elev:.56,zoom:1,px:0,py:0});
  requestDraw();
}
function cameraEvents() {
  const pointers = new Map();
  let pinchDistance = 0;
  const distance = () => {
    const points = [...pointers.values()];
    return Math.hypot(points[0].x-points[1].x, points[0].y-points[1].y);
  };
  els.canvas.addEventListener('pointerdown',e=>{
    pointers.set(e.pointerId,{x:e.clientX,y:e.clientY,pan:e.shiftKey || e.button===2});
    els.canvas.setPointerCapture(e.pointerId);
    pinchDistance = pointers.size === 2 ? distance() : 0;
  });
  els.canvas.addEventListener('pointermove',e=>{
    const prev = pointers.get(e.pointerId);
    if(!prev)return;
    const dx=e.clientX-prev.x,dy=e.clientY-prev.y;
    pointers.set(e.pointerId,{...prev,x:e.clientX,y:e.clientY});
    if(pointers.size>=2){
      const next=distance();
      if(pinchDistance>0&&next>0){
        cam.zoom=Math.max(.25,Math.min(6,cam.zoom*next/pinchDistance));
        requestDraw();
      }
      pinchDistance=next;
      return;
    }
    if(prev.pan){cam.px+=dx;cam.py+=dy;}
    else{cam.yaw+=dx*.012;cam.elev=Math.max(.13,Math.min(1.5,cam.elev-dy*.007));}
    requestDraw();
  });
  const endPointer = e => { pointers.delete(e.pointerId);pinchDistance=0; };
  for(const name of ['pointerup','pointercancel','lostpointercapture'])
    els.canvas.addEventListener(name,endPointer);
  els.canvas.addEventListener('contextmenu',e=>e.preventDefault());
  els.canvas.addEventListener('wheel',e=>{
    e.preventDefault();cam.zoom=Math.max(.25,Math.min(6,cam.zoom*Math.exp(-e.deltaY*.0012)));
    requestDraw();
  },{passive:false});
  $('rotateL').addEventListener('click',()=>{cam.yaw-=Math.PI/2;requestDraw();});
  $('rotateR').addEventListener('click',()=>{cam.yaw+=Math.PI/2;requestDraw();});
  $('topView').addEventListener('click',()=>{cam.elev=1.5;requestDraw();});
  $('resetCam').addEventListener('click',resetCamera);
  if(window.ResizeObserver) new ResizeObserver(requestDraw).observe(els.viewport);
  else window.addEventListener('resize',requestDraw);
  if(window.matchMedia('(pointer: coarse)').matches){
    $('dragHint').textContent='Glisse pour pivoter · Pince pour zoomer · Boutons pour changer de vue';
  }
}

function init() {
  try {
    els.code.value=localStorage.getItem('gabcon-code') ?? SAMPLE;
    els.idea.value=localStorage.getItem('gabcon-idea') || els.idea.value;
  } catch(_){els.code.value=SAMPLE;}
  refreshEditor();downloads(null);cameraEvents();
  els.code.addEventListener('input',refreshEditor);
  els.code.addEventListener('scroll',()=>els.lineNumbers.scrollTop=els.code.scrollTop);
  els.code.addEventListener('keydown',e=>{
    if(e.key==='Tab'){
      e.preventDefault();
      els.code.setRangeText('    ',els.code.selectionStart,els.code.selectionEnd,'end');
      refreshEditor();
    }
  });
  els.idea.addEventListener('input',()=>{
    try{localStorage.setItem('gabcon-idea',els.idea.value);}catch(_){}
  });
  $('copyPrompt').addEventListener('click',copyPrompt);
  $('copyRepair').addEventListener('click',copyRepair);
  $('downloadBrief').addEventListener('click',downloadBrief);
  $('downloadResponse').addEventListener('click',downloadResponse);
  let formatSaved='auto';
  try { formatSaved=localStorage.getItem('gabcon-output-format-direct-v1'); } catch (_) {}
  $('outputFormat').value=GabConPrompt.formatFor(formatSaved);
  $('outputFormat').addEventListener('change',updateOutputFormat);
  updateOutputFormat();
  for (const [id, name, allowed] of [
    ['briefStyle','style',['auto','medieval','modern','fantasy','industrial','natural']],
    ['briefSize','size',['small','medium','large']],
    ['briefDetail','detail',['speed','balanced','detailed']]
  ]) {
    const select=$(id);
    try {
      const saved=localStorage.getItem('gabcon-brief-'+name);
      if (allowed.includes(saved)) select.value=saved;
    } catch (_) {}
    select.addEventListener('change',()=>{
      try { localStorage.setItem('gabcon-brief-'+name,select.value); } catch (_) {}
    });
  }
  $('installBtn').addEventListener('click',installApp);
  $('mobileInstallBtn').addEventListener('click',installApp);
  $('renderMode').value = localStorage.getItem('gabcon-render-mode') === 'quality' ? 'quality' : 'fast';
  $('renderMode').addEventListener('change', () => {
    try { localStorage.setItem('gabcon-render-mode', $('renderMode').value); } catch (_) {}
  });
  els.build.addEventListener('click',build);
  $('exampleBtn').addEventListener('click',()=>{
    if(els.code.value.trim() && els.code.value!==SAMPLE && !confirm('Remplacer le code par la tour de démonstration ?'))return;
    els.code.value=SAMPLE;$('filenameLabel').textContent='blueprint.py';
    refreshEditor();notify('Exemple de tour médiévale chargé.');
  });
  $('fileInput').addEventListener('change',async e=>{
    const file=e.target.files?.[0];if(!file)return;
    if(file.size>500000){notify('Fichier trop volumineux.',true);return;}
    const data=await file.text();
    if (file.name.toLowerCase().endsWith('.json')) {
      try {
        const parsed=JSON.parse(data);
        if (parsed && parsed.schema === 'gabcon-build-brief-v1') {
          if (typeof parsed.description === 'string') {
            els.idea.value=parsed.description;
            try { localStorage.setItem('gabcon-idea',els.idea.value); } catch (_) {}
          }
          const prefs=parsed.preferences || {};
          for (const [id,key] of [['briefStyle','style'],['briefSize','size'],['briefDetail','detail']]) {
            const node=$(id);
            if ([...node.options].some(option=>option.value===prefs[key])) {
              node.value=prefs[key];
              try { localStorage.setItem('gabcon-brief-'+key,node.value); } catch (_) {}
            }
          }
          $('outputFormat').value=GabConPrompt.formatFor(prefs.fileFormat);
          updateOutputFormat();
          notify('Cahier des charges JSON chargé. Copie maintenant le prompt vers ChatGPT.');
          e.target.value='';
          return;
        }
      } catch (_) { /* JSON invalide : le moteur indiquera l'erreur si exécuté. */ }
    }
    const ext=file.name.toLowerCase().split('.').pop();
    if (ext==='mcfunction') $('outputFormat').value='mcfunction';
    else if (ext==='json') {
      try { if (JSON.parse(data)?.schema==='gabcon-block-ops-v1') $('outputFormat').value='json'; }
      catch (_) {}
    } else if (ext==='md' && !/\x60\x60\x60(?:python|py)/i.test(data)) $('outputFormat').value='md';
    else if (ext==='py') $('outputFormat').value='py';
    updateOutputFormat();
    els.code.value=GabConFormats.textForFormat(data,outputFormat());
    $('filenameLabel').textContent=file.name;refreshEditor();
    notify(file.name+' importé.');e.target.value='';
  });
  $('view3d').addEventListener('click',()=>viewMode('3d'));
  $('viewRender').addEventListener('click',()=>viewMode('render'));
  $('refreshHistory').addEventListener('click',refreshHistory);
  document.querySelectorAll('[data-jump]').forEach(button=>
    button.addEventListener('click',()=>$(button.dataset.jump).scrollIntoView({behavior:'smooth'}))
  );
  registerMobileApp();
  requestDraw();refreshHistory();health();
}
init();
