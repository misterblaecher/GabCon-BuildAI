/* Optional Studio local text editor / JSON converter.
 * For direct .schem/.litematic/.nbt/.zip output, download the real binary from ChatGPT.
 * Never create a fake binary by saving ChatGPT text with a binary extension.
 */
'use strict';
(function (root) {
  const FENCE = String.fromCharCode(96).repeat(3);
  const OPS = Object.freeze({
    set_block: ['n','n','n','b'],
    fill: ['n','n','n','n','n','n','b'],
    clear: ['n','n','n','n','n','n'],
    walls: ['n','n','n','n','n','n','b'],
    floor: ['n','n','n','n','n','b'],
    hollow_box: ['n','n','n','n','n','n','b'],
    cylinder: ['n','n','n','n','n','b'],
    sphere: ['n','n','n','n','b'],
    line: ['n','n','n','n','n','n','b']
  });
  const ID = /^(?:[a-z0-9_.-]+:)?[a-z0-9_./-]+(?:\[[a-z0-9_=,.-]+\])?$/;
  function textForFormat(input, format) {
    const text = String(input || '').trim();
    if (!text) return '';
    if (format === 'py') return root.GabConPrompt.extractBlueprint(text);
    if (!canSaveText(format)) throw new Error('Ce format nécessite un vrai fichier binaire généré par ChatGPT.');
    let raw = text;
    const suffix = format === 'md' ? '(?:markdown|md)' : format === 'json' ? 'json' : 'mcfunction';
    const escaped = new RegExp(FENCE + '\\s*' + suffix + '[^\\n]*\\r?\\n([\\s\\S]*?)\\r?\\n' + FENCE, 'i');
    const fenceMatch = raw.match(escaped);
    if (fenceMatch) raw = fenceMatch[1];
    else if (raw[0] === '{') {
      try {
        const obj = JSON.parse(raw);
        if (obj && typeof obj.code === 'string' && format !== 'json') raw = obj.code;
        if (obj && typeof obj.content === 'string' && format !== 'json') raw = obj.content;
      } catch (_) {}
    }
    return raw.trim() + '\n';
  }
  function compileJsonOps(input) {
    const source = textForFormat(input,'json');
    let data;
    try { data = JSON.parse(source); }
    catch (error) { throw new Error('JSON invalide : ' + error.message); }
    if (!data || Array.isArray(data) || data.schema !== 'gabcon-block-ops-v1' || !Array.isArray(data.operations)) {
      throw new Error('Ce fichier doit avoir le schéma gabcon-block-ops-v1 et un tableau operations.');
    }
    if (!data.operations.length || data.operations.length > 1200) {
      throw new Error('Le fichier doit contenir de 1 à 1200 opérations.');
    }
    const code = [];
    data.operations.forEach((operation, index) => {
      if (!operation || Array.isArray(operation) || typeof operation !== 'object') {
        throw new Error('Opération ' + (index+1) + ' invalide.');
      }
      const signature = Object.prototype.hasOwnProperty.call(OPS,operation.op) ? OPS[operation.op] : null;
      if (!signature) throw new Error('Opération ' + (index+1) + ' inconnue : ' + String(operation.op));
      const args=operation.args;
      if (!Array.isArray(args) || args.length !== signature.length) {
        throw new Error('Opération ' + (index+1) + ' : paramètres attendus = ' + signature.length);
      }
      const safe = args.map((value,i) => {
        if (signature[i] === 'n') {
          if (!Number.isInteger(value) || !Number.isSafeInteger(value) || Math.abs(value) > 30000000) {
            throw new Error('Opération ' + (index+1) + ' : coordonnée ou dimension entière invalide.');
          }
          return String(value);
        }
        if (typeof value !== 'string' || value.length > 180 || !ID.test(value)) {
          throw new Error('Opération ' + (index+1) + ' : identifiant de bloc invalide.');
        }
        return JSON.stringify(value);
      });
      code.push(operation.op+'('+safe.join(', ')+')');
    });
    return '# Generated from gabcon-block-ops-v1 JSON; edit the JSON for further changes.\n'+code.join('\n')+'\n';
  }
  function canExecute(format) {
    return ['py','json'].includes(format);
  }
  function canSaveText(format) { return ['py','json','mcfunction','md'].includes(format); }
  function downloadName(format) {
    return {
      py:'blueprint.py', schem:'construction.schem', litematic:'construction.litematic',
      nbt:'construction.nbt', datapack:'gabcon-construction-datapack.zip',
      json:'blueprint.json', mcfunction:'construction.mcfunction', md:'plan-construction.md'
    }[format] || null;
  }
  function contentForBuild(raw, format) {
    if (format==='json') return compileJsonOps(raw);
    if (format==='py') return root.GabConPrompt.extractBlueprint(raw);
    throw new Error('Le format sélectionné n’est pas exécuté par BuildAI. Télécharge le fichier texte.');
  }
  const api={textForFormat,compileJsonOps,canExecute,canSaveText,downloadName,contentForBuild};
  if (typeof module !== 'undefined' && module.exports) {
    // In node tests the prompt helper can be imported before this module.
    if (!root.GabConPrompt) root.GabConPrompt = require('./prompt.js');
    module.exports=api;
  }
  root.GabConFormats=api;
})(typeof window !== 'undefined' ? window : globalThis);
