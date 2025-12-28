'use strict';

function isPlainObject(v) { return !!v && typeof v === 'object' && !Array.isArray(v); }

function addErr(errors, code, message, path) {
  errors.push({ code, message, path: path || '' });
}

function validateOne(rec, index, opts) {
  const errors = [];
  if (!isPlainObject(rec)) { addErr(errors, 'TYPE', 'Record must be a JSON object', ''); return errors; }

  const id = rec.id;
  if (id === undefined || id === null || (typeof id !== 'string' && typeof id !== 'number')) {
    addErr(errors, 'REQUIRED', 'Missing/invalid "id" (string|number)', 'id');
  }

  const input = rec.input;
  if (typeof input !== 'string' || !input.trim()) addErr(errors, 'REQUIRED', 'Missing/invalid "input" (non-empty string)', 'input');

  const anns = rec.annotations;
  if (!Array.isArray(anns)) {
    addErr(errors, 'REQUIRED', 'Missing/invalid "annotations" (array)', 'annotations');
    return errors;
  }

  const maxAnn = (opts && Number.isFinite(opts.maxAnnotationsPerRecord)) ? opts.maxAnnotationsPerRecord : 1000;
  if (anns.length > maxAnn) addErr(errors, 'LIMIT', `Too many annotations (>${maxAnn})`, 'annotations');

  for (let i = 0; i < anns.length; i++) {
    const a = anns[i];
    const pfx = `annotations[${i}]`;
    if (!isPlainObject(a)) { addErr(errors, 'TYPE', 'Annotation must be a JSON object', pfx); continue; }

    const path = a.taxonomyPath;
    if (!Array.isArray(path) || path.length === 0 || !path.every(s => typeof s === 'string' && s.trim())) {
      addErr(errors, 'SCHEMA', 'Missing/invalid "taxonomyPath" (non-empty string array)', `${pfx}.taxonomyPath`);
    }

    if ('value' in a) {
      if (typeof a.value !== 'string' || !a.value.trim()) addErr(errors, 'SCHEMA', '"value" must be a non-empty string when present', `${pfx}.value`);
    } else {
      addErr(errors, 'REQUIRED', 'Missing required "value" (string)', `${pfx}.value`);
    }

    if ('confidence' in a) {
      const c = a.confidence;
      if (typeof c !== 'number' || !(c >= 0 && c <= 1)) addErr(errors, 'SCHEMA', '"confidence" must be a number in [0,1]', `${pfx}.confidence`);
    }

    if ('span' in a) {
      const sp = a.span;
      if (!isPlainObject(sp) || typeof sp.start !== 'number' || typeof sp.end !== 'number' || sp.start < 0 || sp.end < sp.start) {
        addErr(errors, 'SCHEMA', '"span" must be {start:number,end:number} with 0<=start<=end', `${pfx}.span`);
      } else if (typeof input === 'string' && sp.end > input.length) {
        addErr(errors, 'SCHEMA', '"span.end" exceeds input length', `${pfx}.span.end`);
      }
    }
  }

  if ('meta' in rec && rec.meta !== undefined && rec.meta !== null && !isPlainObject(rec.meta)) {
    addErr(errors, 'TYPE', '"meta" must be an object when present', 'meta');
  }

  return errors;
}

function parseJsonl(input) {
  const text = Array.isArray(input) ? input.join('\n') : String(input || '');
  const lines = text.split(/\r?\n/);
  const out = [];
  for (let i = 0; i < lines.length; i++) {
    const raw = lines[i];
    if (!raw || !raw.trim()) continue;
    try { out.push({ ok: true, value: JSON.parse(raw), line: i + 1, raw }); }
    catch (e) { out.push({ ok: false, error: String(e && e.message ? e.message : e), line: i + 1, raw }); }
  }
  return out;
}

function validateAnnotations(jsonlInput, opts) {
  const parsed = parseJsonl(jsonlInput);
  const records = [];
  let total = 0, valid = 0, invalid = 0, parseErrors = 0;

  for (let i = 0; i < parsed.length; i++) {
    const p = parsed[i];
    total++;
    if (!p.ok) {
      parseErrors++; invalid++;
      records.push({ index: i, line: p.line, id: null, ok: false, errors: [{ code: 'PARSE', message: p.error, path: '' }] });
      continue;
    }
    const rec = p.value;
    const errs = validateOne(rec, i, opts);
    const ok = errs.length === 0;
    if (ok) valid++; else invalid++;
    records.push({ index: i, line: p.line, id: (rec && rec.id !== undefined ? rec.id : null), ok, errors: errs });
  }

  const summary = { ok: invalid === 0, totalRecords: total, validRecords: valid, invalidRecords: invalid, parseErrors };
  return { ok: summary.ok, summary, records };
}

module.exports = { validateAnnotations, parseJsonl };
