#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

function readJsonl(filePath) {
  const text = fs.readFileSync(filePath, 'utf8');
  const lines = text.split(/\r?\n/).filter(l => l.trim().length > 0);
  const parsed = [];
  const parseErrors = [];
  for (let i = 0; i < lines.length; i++) {
    try {
      parsed.push({ index: i, ok: true, value: JSON.parse(lines[i]) });
    } catch (e) {
      parseErrors.push({
        index: i,
        ok: false,
        errors: [{ code: 'json_parse_error', message: String(e && e.message ? e.message : e), line: lines[i] }]
      });
    }
  }
  return { parsed, parseErrors, lineCount: lines.length };
}

function pickValidator(mod) {
  if (!mod) return null;
  if (typeof mod === 'function') return mod;
  if (typeof mod.validateAnnotations === 'function') return mod.validateAnnotations;
  if (mod.default && typeof mod.default === 'function') return mod.default;
  if (mod.default && typeof mod.default.validateAnnotations === 'function') return mod.default.validateAnnotations;
  return null;
}

function normalizeResult(res, parseErrors, lineCount) {
  const out = {
    ok: false,
    summary: { ok: false, total: lineCount, valid: 0, invalid: lineCount, parse_errors: parseErrors.length },
    records: [],
  };

  const byIndex = new Map();
  for (const pe of parseErrors) byIndex.set(pe.index, { index: pe.index, ok: false, errors: pe.errors });

  const r = res && typeof res === 'object' ? res : {};
  const recs =
    Array.isArray(r.records) ? r.records :
    Array.isArray(r.results) ? r.results :
    Array.isArray(r.perRecord) ? r.perRecord :
    null;

  if (recs) {
    for (const rec of recs) {
      const idx = Number.isInteger(rec.index) ? rec.index :
                  Number.isInteger(rec.line) ? rec.line :
                  Number.isInteger(rec.i) ? rec.i : null;
      const ok = rec.ok === true || rec.valid === true;
      const errs = Array.isArray(rec.errors) ? rec.errors :
                   Array.isArray(rec.issues) ? rec.issues :
                   (rec.error ? [rec.error] : []);
      if (idx === null) continue;
      if (byIndex.has(idx)) continue; // parse error wins
      byIndex.set(idx, { index: idx, ok, errors: ok ? [] : errs });
    }
  }

  for (let i = 0; i < lineCount; i++) {
    if (!byIndex.has(i)) byIndex.set(i, { index: i, ok: true, errors: [] });
  }

  out.records = Array.from(byIndex.values()).sort((a, b) => a.index - b.index);
  out.summary.total = lineCount;
  out.summary.valid = out.records.filter(x => x.ok).length;
  out.summary.invalid = out.records.filter(x => !x.ok).length;
  out.summary.ok = out.summary.invalid === 0;

  if (r.summary && typeof r.summary === 'object') {
    out.summary = Object.assign({}, out.summary, r.summary, { ok: out.summary.ok });
  }
  out.ok = out.summary.ok;
  return out;
}

(async function main() {
  const repoRoot = path.resolve(__dirname, '..');
  const fixturePath = process.env.TAXONOMY_FIXTURE_PATH
    ? path.resolve(process.env.TAXONOMY_FIXTURE_PATH)
    : path.join(repoRoot, 'tests', 'fixtures', 'taxonomy', 'annotations_fixture.jsonl');
  const reportDir = path.join(repoRoot, 'runtime', '_build', 'reports');
  const reportPath = path.join(reportDir, 'taxonomy_validation.json');

  fs.mkdirSync(reportDir, { recursive: true });

  let parse;
  try {
    parse = readJsonl(fixturePath);
  } catch (e) {
    const fail = { ok: false, summary: { ok: false, total: 0, valid: 0, invalid: 0, parse_errors: 0 }, records: [], error: String(e && e.message ? e.message : e) };
    fs.writeFileSync(reportPath, JSON.stringify(fail, null, 2) + '\n', 'utf8');
    console.error('taxonomy:validate failed to read fixture:', fail.error);
    process.exit(2);
    return;
  }

  let validatorMod;
  try {
    validatorMod = require(path.join(repoRoot, 'src', 'taxonomy', 'validate_annotations.js'));
  } catch (e) {
    const fail = {
      ok: false,
      summary: { ok: false, total: parse.lineCount, valid: 0, invalid: parse.lineCount, parse_errors: parse.parseErrors.length },
      records: parse.parseErrors,
      error: 'Failed to load validator: ' + String(e && e.message ? e.message : e),
    };
    fs.writeFileSync(reportPath, JSON.stringify(fail, null, 2) + '\n', 'utf8');
    console.error(fail.error);
    process.exit(2);
    return;
  }

  const validate = pickValidator(validatorMod);
  if (!validate) {
    const fail = {
      ok: false,
      summary: { ok: false, total: parse.lineCount, valid: 0, invalid: parse.lineCount, parse_errors: parse.parseErrors.length },
      records: parse.parseErrors,
      error: 'Validator module does not export a callable validator',
    };
    fs.writeFileSync(reportPath, JSON.stringify(fail, null, 2) + '\n', 'utf8');
    console.error(fail.error);
    process.exit(2);
    return;
  }

  const validRecords = parse.parsed.filter(x => x.ok).map(x => x.value);

  let res;
  try {
    res = await Promise.resolve(validate(validRecords, { fixturePath }));
  } catch (e) {
    res = { summary: { ok: false }, records: [], error: String(e && e.message ? e.message : e) };
  }

  const report = normalizeResult(res, parse.parseErrors, parse.lineCount);
  report.meta = { fixturePath, reportPath, generated_at: new Date().toISOString() };
  if (res && typeof res === 'object' && res.error) report.error = res.error;

  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n', 'utf8');

  if (!report.ok) {
    console.error(`taxonomy:validate failed (${report.summary.invalid}/${report.summary.total} invalid). Report: ${reportPath}`);
    process.exitCode = 1;
  } else {
    console.log(`taxonomy:validate passed (${report.summary.valid}/${report.summary.total}). Report: ${reportPath}`);
  }
})();
