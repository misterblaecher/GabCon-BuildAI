// Browser/Node contract tests for each ChatGPT file type and the JSON -> DSL bridge.
'use strict';
const assert = require('node:assert/strict');
const Prompt = require('../gabcon-studio/static/prompt.js');
const Formats = require('../gabcon-studio/static/formats.js');

for (const fileFormat of ['py','schem','json','mcfunction','md']) {
  const brief = Prompt.createBrief({
    idea: 'Tour fortifiée près de la rivière', style:'medieval',
    size:'small',detail:'balanced',blockLimit:300000,fileFormat
  });
  assert.equal(brief.preferences.fileFormat,fileFormat);
  assert.equal(brief.deliverable.filename,Prompt.getFormat(fileFormat).filename);
  assert.ok(Prompt.getFormat(fileFormat).good.length>25);
  assert.ok(Prompt.getFormat(fileFormat).bad.length>25);
  assert.ok(Prompt.getFormat(fileFormat).workflow.length>25);
  const prompt=Prompt.buildPrompt(brief);
  assert.match(prompt,/Tour fortifiée/);
  if (fileFormat==='py') {
    assert.match(prompt,/blueprint.py/);
    assert.match(prompt,/run_blueprint/);
    assert.match(prompt,/floor\(x1, z1, x2, z2, y/);
  } else if (fileFormat==='schem') {
    assert.match(prompt,/NBT gzip/);
    assert.match(prompt,/final.schem/);
    assert.match(prompt,/blueprint.py/);
    assert.match(prompt,/faux binaire/);
  } else if (fileFormat==='json') {
    assert.match(prompt,/gabcon-block-ops-v1/);
    assert.match(prompt,/JSON valide/);
    assert.match(prompt,/1200 opérations/);
    assert.doesNotMatch(prompt,/RENVOIE UNIQUEMENT un bloc Markdown.*mcfunction/);
  } else if (fileFormat==='mcfunction') {
    assert.match(prompt,/32768 blocs/);
    assert.match(prompt,/sans.*\//i);
    assert.match(prompt,/datapack/i);
  } else if (fileFormat==='md') {
    assert.match(prompt,/Markdown/);
    assert.match(prompt,/Dimensions/);
    assert.match(prompt,/Ne fournis ni binaire/);
  }
}
assert.equal(Prompt.formatFor('bad_type'),'py');
assert.equal(Formats.downloadName('schem'),'blueprint.py');
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
assert.equal(Formats.textForFormat('text\n```python\nset_block(0,0,0,"stone")\n```','schem'),
  'set_block(0,0,0,"stone")\n');

const bad = JSON.stringify({schema:'gabcon-block-ops-v1',operations:[{op:'eval',args:[]}]});
assert.throws(()=>Formats.compileJsonOps(bad),/inconnue/);
assert.throws(()=>Formats.compileJsonOps(JSON.stringify({...ops,operations:[{op:'set_block',args:[0,0,0,'stone");__import__("os"'] }]})),/invalide/);
assert.throws(()=>Formats.compileJsonOps('{garbage}'),/JSON invalide/);
assert.throws(()=>Formats.compileJsonOps(JSON.stringify({...ops,operations:[]})),/1 à 1200/);
assert.throws(()=>Formats.contentForBuild('fill 0 0 0 1 0 1 stone','mcfunction'),/ne s’exécute pas/);

const brief=Prompt.createBrief({fileFormat:'json',idea:'Tour'});
const repaired=Prompt.repairJsonPrompt(brief,JSON.stringify(ops),'Erreur de palette');
assert.match(repaired,/gabcon-block-ops-v1/);
assert.match(repaired,/Erreur de palette/);
assert.match(repaired,/JSON COMPLET/);

console.log('GabCon Studio file-type prompt and safe JSON conversion tests passed');
