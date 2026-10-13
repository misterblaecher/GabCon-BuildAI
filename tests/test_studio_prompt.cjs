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
assert.equal(fallback.architectural_style.startsWith('Aucun style'), true);
assert.equal(fallback.preferences.creationType, 'auto');
assert.equal(fallback.preferences.organicSubject, 'auto');
assert.equal(fallback.preferences.fileFormat, 'auto');
assert.equal(fallback.deliverable.filename, null);


const Prompt = require('../gabcon-studio/static/prompt.js');
const kindIds=Prompt.getCreationTypes().map(item=>item.id);
assert.deepEqual(kindIds,['auto','architecture','organic','landscape','sculpture','pixelart']);
const subjects=Prompt.getOrganicSubjects().map(item=>item.id);
assert.deepEqual(subjects,['auto','creature','humanoid','dragon','vegetation','abstract']);

const styles=Prompt.getStylesForType('organic').map(item=>item.id);
assert.ok(styles.includes('realistic'));
assert.ok(styles.includes('fantasy'));
assert.ok(styles.includes('cartoon'));
assert.ok(styles.includes('biomechanical'));
assert.equal(styles.includes('medieval'),false);
assert.ok(Prompt.getStylesForType('architecture').some(item=>item.id==='gothic'));
assert.ok(Prompt.getStylesForType('architecture').some(item=>item.id==='japanese'));
assert.ok(Prompt.getStylesForType('auto').length>12);

const organic=Prompt.createBrief({
  idea:'Dragon gigantesque aux ailes déployées',
  fileFormat:'schem',creationType:'organic',organicSubject:'dragon',
  style:'fantasy',detail:'detailed',size:'large'
});
assert.equal(organic.preferences.creationType,'organic');
assert.equal(organic.preferences.organicSubject,'dragon');
assert.equal(organic.visual_style.label,'Fantasy');
assert.match(organic.creation_kind.description,/dragon/i);
assert.match(organic.organic_subject.description,/ailes/i);
const organicPrompt=Prompt.buildPrompt(organic);
assert.match(organicPrompt,/TYPE DE CRÉATION : Organique/);
assert.match(organicPrompt,/SUJET ORGANIQUE : Dragon/);
assert.match(organicPrompt,/SILHOUETTE ORGANIQUE/);
assert.match(organicPrompt,/360°/);
assert.match(organicPrompt,/construction\.schem/);
assert.match(organicPrompt,/STYLE VISUEL : Fantasy/);

for (const format of ['auto','schem','litematic','nbt','datapack','mcfunction','py','json','md']) {
  const briefOrg=Prompt.createBrief({
    idea:'Arbre colossal',creationType:'organic',organicSubject:'vegetation',
    style:'natural',fileFormat:format
  });
  const adapted=Prompt.buildPrompt(briefOrg);
  assert.match(adapted,/SUJET ORGANIQUE : Arbre/);
  assert.match(adapted,/Tronc|branches|racines|feuillage/i);
  assert.match(adapted,/MODELER EN 3D/);
}
const gothic=Prompt.createBrief({creationType:'architecture',style:'gothic'});
assert.match(Prompt.buildPrompt(gothic),/STYLE VISUEL : Gothique/);
assert.match(Prompt.buildPrompt(gothic),/volumes habitables/);
const terrain=Prompt.createBrief({creationType:'landscape',style:'natural'});
assert.match(Prompt.buildPrompt(terrain),/courbes de niveau/);
const pixel=Prompt.createBrief({creationType:'pixelart',style:'stylized'});
assert.match(Prompt.buildPrompt(pixel),/PIXEL ART :/);
const incompatible=Prompt.createBrief({creationType:'organic',style:'medieval',organicSubject:'unexpected'});
assert.equal(incompatible.preferences.style,'auto');
assert.equal(incompatible.preferences.organicSubject,'auto');
const notOrganic=Prompt.createBrief({creationType:'architecture',organicSubject:'dragon'});
assert.equal(notOrganic.organic_subject,null);
assert.equal(notOrganic.preferences.organicSubject,'auto');

console.log('GabCon Studio AI brief, organic geometry and style prompt contract tests passed');
