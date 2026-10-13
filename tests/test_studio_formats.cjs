// Browser/Node contract tests for each ChatGPT file type and the JSON -> DSL bridge.
'use strict';
const assert = require('node:assert/strict');
const Prompt = require('../gabcon-studio/static/prompt.js');
const Formats = require('../gabcon-studio/static/formats.js');

for (const fileFormat of ['auto','schem','litematic','nbt','datapack','mcfunction','py','json','md']) {
  const brief = Prompt.createBrief({
    idea: 'Tour fortifiée près de la rivière', style:'medieval',
    size:'small',detail:'balanced',blockLimit:300000,fileFormat
  });
  assert.equal(brief.preferences.fileFormat,fileFormat);
  assert.equal(brief.deliverable.filename,Prompt.getFormat(fileFormat).filename);
  assert.ok(Prompt.getFormat(fileFormat).good.length>25);
  assert.ok(Prompt.getFormat(fileFormat).bad.length>25);
  assert.ok(Prompt.getFormat(fileFormat).workflow.length>25);
  assert.ok(Prompt.getFormat(fileFormat).difficulty.length>4);
  assert.ok(['auto','game','intermediate','document'].includes(Prompt.getFormat(fileFormat).category));
  assert.equal(Prompt.getFormat(fileFormat).gameReady,
    ['schem','litematic','nbt','datapack'].includes(fileFormat));
  assert.equal(brief.deliverable.generation,'directly_in_chatgpt_without_gabcon_studio');
  const prompt=Prompt.buildPrompt(brief);
  assert.match(prompt,/Tour fortifiée/);
  assert.match(prompt,/vrais? fichiers? téléchargeables?/i);
  assert.doesNotMatch(prompt,/GitHub Actions comme moteur/i);
  if (fileFormat==='auto') {
    assert.equal(brief.deliverable.filename, null);
    assert.match(prompt,/AUCUN TYPE DE FICHIER N’EST IMPOSÉ/);
    assert.match(prompt,/ChatGPT choisit|Choisis librement/);
    assert.doesNotMatch(prompt,/Sponge Schematic v3/);
    assert.doesNotMatch(prompt,/construction\.mcfunction/);
  } else if (fileFormat==='py') {
    assert.match(prompt,/blueprint.py/);
    assert.match(prompt,/run_blueprint/);
    assert.match(prompt,/floor\(x1, z1, x2, z2, y/);
  } else if (fileFormat==='schem') {
    assert.match(prompt,/NBT gzip/);
    assert.match(prompt,/construction.schem/);
    assert.match(prompt,/outil de code\/fichiers/);
    assert.match(prompt,/faux lien/);
    assert.doesNotMatch(prompt,/GabCon Studio le transformera/);
  } else if (fileFormat==='litematic') {
    assert.match(prompt,/BlockStatePalette/);
    assert.match(prompt,/BlockStates/);
    assert.match(prompt,/TAG_Long_Array/);
    assert.match(prompt,/Forgematica/);
    assert.match(prompt,/MaFgLib/);
    assert.match(prompt,/construction.litematic/);
    assert.match(prompt,/Ne renomme jamais un .schem en .litematic/);
  } else if (fileFormat==='nbt') {
    assert.match(prompt,/construction.nbt/);
    assert.match(prompt,/DataVersion=3955/);
    assert.match(prompt,/palette/);
    assert.match(prompt,/\/place template/);
    assert.doesNotMatch(prompt,/fichier WorldEdit .schem\s*pour/);
  } else if (fileFormat==='datapack') {
    assert.match(prompt,/gabcon-construction-datapack.zip/);
    assert.match(prompt,/pack_format":48/);
    assert.match(prompt,/data\/gabcon\/function\/construction.mcfunction/);
    assert.match(prompt,/\/function/);
  } else if (fileFormat==='json') {
    assert.match(prompt,/gabcon-block-ops-v1/);
    assert.match(prompt,/JSON valide/);
    assert.match(prompt,/1200 opérations/);
    assert.match(prompt,/Minecraft vanilla ne lit pas ce JSON/);
    assert.doesNotMatch(prompt,/RENVOIE UNIQUEMENT un bloc Markdown.*mcfunction/);
  } else if (fileFormat==='mcfunction') {
    assert.match(prompt,/32768 blocs/);
    assert.match(prompt,/sans slash initial/i);
    assert.match(prompt,/datapack/i);
  } else if (fileFormat==='md') {
    assert.match(prompt,/Markdown/);
    assert.match(prompt,/Dimensions/);
    assert.match(prompt,/un plan de conception|non une construction importable/i);
  }
}
assert.equal(Prompt.formatFor('bad_type'),'auto');
assert.equal(Prompt.formatFor(null),'auto');
assert.equal(Prompt.formatFor(''),'auto');
assert.equal(Formats.canExecute('auto'),false);
assert.equal(Formats.downloadName('schem'),'construction.schem');
assert.equal(Formats.downloadName('litematic'),'construction.litematic');
assert.equal(Formats.downloadName('nbt'),'construction.nbt');
assert.equal(Formats.downloadName('datapack'),'gabcon-construction-datapack.zip');
assert.equal(Formats.canExecute('schem'),false);
assert.equal(Formats.canExecute('litematic'),false);
assert.equal(Formats.canExecute('nbt'),false);
assert.equal(Formats.canExecute('datapack'),false);
assert.equal(Formats.canSaveText('schem'),false);
assert.equal(Formats.canSaveText('litematic'),false);
assert.equal(Formats.canSaveText('nbt'),false);
assert.equal(Formats.canSaveText('datapack'),false);
assert.equal(Formats.canSaveText('mcfunction'),true);
assert.equal(Formats.canSaveText('json'),true);
assert.equal(Formats.canSaveText('py'),true);
assert.equal(Formats.downloadName('mcfunction'),'construction.mcfunction');
assert.equal(Formats.canExecute('mcfunction'),false);
assert.equal(Formats.canExecute('md'),false);
assert.equal(Formats.canExecute('json'),true);

const ops={
  schema:'gabcon-block-ops-v1',
  operations:[
    {op:'floor',args:[-3,-3,3,3,0,'oak_planks']},
    {op:'walls',args:[-3,-3,3,3,1,4,'stone_bricks']},
    {op:'fill',args:[-1,1,-3,1,2,-3,'air']},
    {op:'cylinder',args:[0,0,5,2,3,'spruce_planks']},
  ]
};
const parsed=Formats.compileJsonOps('Voici le fichier:\n```json\n'+JSON.stringify(ops)+'\n```');
assert.match(parsed,/floor\(-3, -3, 3, 3, 0, "oak_planks"\)/);
assert.match(parsed,/walls\(-3, -3, 3, 3, 1, 4, "stone_bricks"\)/);
assert.match(parsed,/cylinder\(0, 0, 5, 2, 3, "spruce_planks"\)/);
assert.equal(parsed,Formats.contentForBuild(JSON.stringify(ops),'json'));
assert.equal(Formats.textForFormat('hi\n```mcfunction\nfill 0 0 0 4 0 4 minecraft:stone\n```','mcfunction'),
  'fill 0 0 0 4 0 4 minecraft:stone\n');
assert.equal(Formats.textForFormat('text\n```markdown\n# Plan\n```','md'),'# Plan\n');
assert.equal(Formats.textForFormat('text\n```python\nset_block(0,0,0,"stone")\n```','py'),
  'set_block(0,0,0,"stone")\n');
for (const binary of ['schem','litematic','nbt','datapack']) {
  assert.throws(() => Formats.textForFormat('fake binary',binary),/vrai fichier binaire/);
  assert.throws(() => Formats.contentForBuild('fake',binary),/n’est pas exécuté/);
}

const bad = JSON.stringify({schema:'gabcon-block-ops-v1',operations:[{op:'eval',args:[]}]});
assert.throws(()=>Formats.compileJsonOps(bad),/inconnue/);
assert.throws(()=>Formats.compileJsonOps(JSON.stringify({...ops,operations:[{op:'set_block',args:[0,0,0,'stone");__import__("os"'] }]})),/invalide/);
assert.throws(()=>Formats.compileJsonOps('{garbage}'),/JSON invalide/);
assert.throws(()=>Formats.compileJsonOps(JSON.stringify({...ops,operations:[]})),/1 à 1200/);
assert.throws(()=>Formats.contentForBuild('fill 0 0 0 1 0 1 stone','mcfunction'),/n’est pas exécuté/);

const brief=Prompt.createBrief({fileFormat:'json',idea:'Tour'});
const repaired=Prompt.repairJsonPrompt(brief,JSON.stringify(ops),'Erreur de palette');
assert.match(repaired,/gabcon-block-ops-v1/);
assert.match(repaired,/Erreur de palette/);
assert.match(repaired,/JSON COMPLET/);


/* UI regression: direct ChatGPT and local BuildAI remain independent controls.
   The nine format buttons are built from metadata containing visible pros/cons. */
const fs=require('node:fs');
const path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'../gabcon-studio/static/index.html'),'utf8');
const app=fs.readFileSync(path.join(__dirname,'../gabcon-studio/static/app.js'),'utf8');
assert.match(html,/id="chatgptWorkflow"/);
assert.match(html,/id="engineWorkflow"/);
assert.match(html,/id="formatChoices"/);
assert.doesNotMatch(html,/<select[^>]*id="outputFormat"/);
assert.match(html,/data-engine-format="py"/);
assert.match(html,/data-engine-format="json"/);
assert.match(html,/id="briefInput"/);
assert.match(html,/id="fileInput"/);
assert.match(app,/button\.type='button'/);
assert.match(app,/button\.setAttribute\('aria-pressed'/);
assert.match(app,/positive\.append\(plus,document\.createTextNode\(' '\+info\.good\)\)/);
assert.match(app,/negative\.append\(minus,document\.createTextNode\(' '\+info\.bad\)\)/);
assert.match(app,/setOutputFormat\(format\)/);
for(const option of ['auto','schem','litematic','nbt','datapack','mcfunction','py','json','md']) {
  assert.match(app.slice(app.indexOf('const PROMPT_FORMAT_GROUPS'),app.indexOf('function outputFormat()')),new RegExp("'"+option+"'"));
}
const builder=app.slice(app.indexOf('async function build()'),app.indexOf('async function refreshHistory()'));
assert.match(builder,/const format=engineInputFormat/);
assert.doesNotMatch(builder,/outputFormat\(|selectedPromptFormat/);
const chooseChatGpt=app.slice(app.indexOf('function updateOutputFormat()'),app.indexOf('function setEngineFormat('));
assert.doesNotMatch(chooseChatGpt,/engineInputFormat|els\.build|downloadResponse/);
const chooseEngine=app.slice(app.indexOf('function setEngineFormat('),app.indexOf('function downloadResponse()'));
assert.doesNotMatch(chooseEngine,/selectedPromptFormat|setOutputFormat\(/);
assert.match(app,/setOutputFormat\(prefs\.fileFormat\)/);
assert.match(app,/setEngineFormat\(fileFormat\)/);
assert.match(app,/const format=engineInputFormat/);


assert.match(html,/id="creationKindChoices"/);
assert.match(html,/id="organicSubjectChoices"/);
assert.match(html,/id="organicSubjectWrap"[^>]*hidden/);
assert.match(html,/id="briefStyle"/);
assert.match(html,/id="styleHint"/);
assert.match(html,/id="organicExampleBtn"/);
assert.match(app,/function setCreationType\(/);
assert.match(app,/function setOrganicSubject\(/);
assert.match(app,/function refreshStyleChoices\(/);
assert.match(app,/function initCreationControls\(/);
assert.match(app,/button\.dataset\[type==='organic'/);
assert.match(app,/aria-pressed/);
assert.match(app,/setCreationType\(prefs\.creationType\)/);
assert.match(app,/setOrganicSubject\(prefs\.organicSubject\)/);
assert.match(app,/SAMPLE_ORGANIC/);
assert.match(app,/sphere\(0, 24, 0/);
assert.match(app,/setEngineFormat\('py'\);els\.code\.value=SAMPLE_ORGANIC/);
assert.match(app,/creationType:selectedCreationType,organicSubject:selectedOrganicSubject/);
assert.doesNotMatch(builder,/selectedCreationType|selectedOrganicSubject|briefStyle/);
const kinds=Prompt.getCreationTypes().map(item=>item.id);
assert.deepEqual(kinds,['auto','architecture','organic','landscape','sculpture','pixelart']);
for(const subject of ['creature','humanoid','dragon','vegetation','abstract']) {
  assert.ok(Prompt.getOrganicSubjects().some(item=>item.id===subject));
}

console.log('GabCon Studio creative-type, organic subject, style and engine independence tests passed');
