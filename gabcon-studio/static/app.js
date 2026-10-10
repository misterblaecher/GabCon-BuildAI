'use strict';

// ChatGPT runs outside this application. Studio only handles a pasted mcbuild DSL blueprint.
const $ = id => document.getElementById(id);
const els = {
  code: $('code'), idea: $('idea'), seed: $('seed'), canvas: $('voxelCanvas'),
  image: $('renderImage'), viewport: $('viewport'), toast: $('toast'),
  build: $('buildBtn'), lineNumbers: $('lineNumbers'), history: $('historyGrid')
};
let current = null, model = null, mode = '3d', busy = false, toastTimer = 0;
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
  busy = active;
  els.build.disabled = active;
  $('buildBtnText').textContent = active ? 'Construction en cours...' : 'Visualiser la construction';
  $('buildBtnIcon').textContent = active ? '◌' : '◩';
  $('processing').classList.toggle('hidden', !active);
  if (active) status('GÉNÉRATION...');
}
function extractCode(s) {
  const found = s.match(/```(?:python|py)?\s*\n([\s\S]*?)\n```/i);
  return found ? found[1].trim() + '\n' : s;
}
function refreshEditor() {
  const lines = els.code.value.split('\n').length;
  els.lineNumbers.textContent = Array.from({ length: lines }, (_, n) => n + 1).join('\n');
  $('codeCount').textContent = lines + (lines > 1 ? ' lignes' : ' ligne');
  try { localStorage.setItem('gabcon-code', els.code.value); } catch (_) {}
}
function blueprintPrompt() {
  return [
    'Tu es architecte Minecraft et tu connais parfaitement le DSL Python de GabCon-BuildAI (mcbuild).',
    'Projet : ' + (els.idea.value.trim() || 'Une construction Minecraft détaillée'),
    '',
    'Réponds UNIQUEMENT avec du code Python compatible avec mcbuild.dsl.sandbox.run_blueprint.',
    'Fonctions disponibles :',
    'set_block(x, y, z, "stone_bricks")',
    'fill(x1, y1, z1, x2, y2, z2, "spruce_planks")',
    'cylinder(cx, cz, y, height, r, "stone_bricks", hollow=False)',
    'sphere(cx, cy, cz, r, "stone_bricks", hollow=False)',
    'Boucles for/range, if, variables et listes Python simples sont autorisées.',
    'Le bloc "air" sert à créer des ouvertures.',
    'Les coordonnées X/Z sont horizontales, Y est verticale.',
    'Aucun import, aucune API externe, pas de fonctions inexistantes.',
    'Utilise des blocs Minecraft valides et limite la construction à 160 000 blocs.',
    'Ajoute des détails, des entrées et une architecture cohérente.',
    'Le script sera collé directement dans GabCon Studio.',
    'Documentation : https://github.com/misterblaecher/GabCon-BuildAI/blob/main/src/mcbuild/dsl/REFERENCE.md'
  ].join('\n');
}
async function copyPrompt() {
  const value = blueprintPrompt();
  try {
    await navigator.clipboard.writeText(value);
    notify('Prompt copié ! Colle-le dans ChatGPT, puis copie le Python ici.');
  } catch (_) {
    const temp = document.createElement('textarea');
    temp.value = value;
    temp.style.cssText = 'position:fixed;left:-10000px';
    document.body.appendChild(temp); temp.select();
    const ok = document.execCommand('copy');
    temp.remove();
    notify(ok ? 'Prompt copié pour ChatGPT.' : 'La copie automatique est indisponible.', !ok);
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
  $('previewSubtitle').textContent = item.name;
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
      notify('Projet volumineux : visualisation par PNG.');
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
  const source = extractCode(els.code.value);
  if (!source.trim()) return notify('Colle d’abord du code Python.', true);
  const seed = Number(els.seed.value);
  if (!Number.isInteger(seed) || seed < 0 || seed > 2147483647) return notify('Seed invalide.', true);
  if (source !== els.code.value) { els.code.value = source; refreshEditor(); }
  loading(true);
  try {
    const response = await fetch('/api/build', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({source, name:els.idea.value.trim() || 'Construction', seed})
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
    notify(err.message || 'Erreur inconnue', true);
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
  let drag=null;
  els.canvas.addEventListener('pointerdown',e=>{
    drag={x:e.clientX,y:e.clientY,pan:e.shiftKey || e.button===2};
    els.canvas.setPointerCapture(e.pointerId);
  });
  els.canvas.addEventListener('pointermove',e=>{
    if(!drag)return;
    const dx=e.clientX-drag.x,dy=e.clientY-drag.y;
    drag.x=e.clientX;drag.y=e.clientY;
    if(drag.pan){cam.px+=dx;cam.py+=dy;}
    else{cam.yaw+=dx*.012;cam.elev=Math.max(.13,Math.min(1.5,cam.elev-dy*.007));}
    requestDraw();
  });
  for(const name of ['pointerup','pointercancel','lostpointercapture'])
    els.canvas.addEventListener(name,()=>{drag=null;});
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
  els.build.addEventListener('click',build);
  $('exampleBtn').addEventListener('click',()=>{
    if(els.code.value.trim() && els.code.value!==SAMPLE && !confirm('Remplacer le code par la tour de démonstration ?'))return;
    els.code.value=SAMPLE;$('filenameLabel').textContent='blueprint.py';
    refreshEditor();notify('Exemple de tour médiévale chargé.');
  });
  $('fileInput').addEventListener('change',async e=>{
    const file=e.target.files?.[0];if(!file)return;
    if(file.size>500000){notify('Fichier trop volumineux.',true);return;}
    els.code.value=extractCode(await file.text());
    $('filenameLabel').textContent=file.name;refreshEditor();
    notify(file.name+' importé.');e.target.value='';
  });
  $('view3d').addEventListener('click',()=>viewMode('3d'));
  $('viewRender').addEventListener('click',()=>viewMode('render'));
  $('refreshHistory').addEventListener('click',refreshHistory);
  document.querySelectorAll('[data-jump]').forEach(button=>
    button.addEventListener('click',()=>$(button.dataset.jump).scrollIntoView({behavior:'smooth'}))
  );
  requestDraw();refreshHistory();health();
}
init();
