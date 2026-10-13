// Contract tests: no API or LLM is called; all examples are generated locally.
const assert = require('node:assert/strict');
const { createBrief, buildPrompt, repairPrompt, extractBlueprint } = require('../gabcon-studio/static/prompt.js');

const brief = createBrief({
  idea: 'Une cathédrale médiévale avec un clocher', style: 'medieval',
  size: 'small', detail: 'detailed', blockLimit: 160000, fileFormat:'py'
});
assert.equal(brief.schema, 'gabcon-build-brief-v1');
assert.equal(brief.deliverable.filename, 'blueprint.py');
assert.equal(brief.deliverable.export_by_engine, null);
assert.equal(brief.deliverable.generation, 'directly_in_chatgpt_without_gabcon_studio');
assert.equal(brief.limits.max_placed_blocks, 160000);
assert.equal(brief.approximate_dimensions.width_x, 24);
assert.equal(brief.approximate_dimensions.height_y, 20);
assert.equal(brief.architectural_style.includes('Médiéval'), true);

const prompt = buildPrompt(brief);
assert.match(prompt, /\.py/);
assert.match(prompt, /cylinder\(cx, cz, y, height, r/);
assert.match(prompt, /floor\(x1, z1, x2, z2, y/);
assert.match(prompt, /AUCUN import/);
assert.match(prompt, /160000/);
assert.match(prompt, /directement ici/);
assert.match(prompt, /fichier texte blueprint\.py/);
assert.match(prompt, /un seul bloc python/);

const fenced = [
  'Voici ton code :',
  '\x60\x60\x60python',
  'fill(0, 0, 0, 4, 0, 4, "stone")',
  '\x60\x60\x60',
  'Bonne construction !',
].join('\n');
assert.equal(extractBlueprint(fenced), 'fill(0, 0, 0, 4, 0, 4, "stone")\n');
assert.equal(extractBlueprint(JSON.stringify({ code: 'set_block(1,2,3,"glass")' })),
  'set_block(1,2,3,"glass")\n');
assert.equal(extractBlueprint(' set_block(0,0,0,"stone")  '), 'set_block(0,0,0,"stone")\n');
assert.equal(extractBlueprint(''), '');

const repaired = repairPrompt(brief, fenced, 'BlueprintError: unknown block');
assert.match(repaired, /unknown block/);
assert.match(repaired, /fill\(0, 0, 0/);
assert.match(repaired, /fichier blueprint.py COMPLET/);
assert.throws(() => repairPrompt(brief, '', 'erreur'), /Aucun blueprint/);

const fallback = createBrief({
  idea: ' ', style: 'invalid', size: 'invalid',
  detail: 'invalid', blockLimit: 999999999
});
assert.equal(fallback.limits.max_placed_blocks, 4000000);
assert.equal(fallback.approximate_dimensions.width_x, 48);
assert.equal(fallback.architectural_style.startsWith('Respecter'), true);
assert.equal(fallback.preferences.fileFormat, 'auto');
assert.equal(fallback.deliverable.filename, null);

console.log('GabCon Studio AI brief and repair contract tests passed');
