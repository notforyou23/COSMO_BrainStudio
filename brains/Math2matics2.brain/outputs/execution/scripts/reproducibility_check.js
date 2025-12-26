#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execSync } = require('child_process');

function die(msg, code = 1) { console.error(msg); process.exit(code); }
function exists(p) { try { fs.accessSync(p); return true; } catch { return false; } }
function rmrf(p) { if (exists(p)) fs.rmSync(p, { recursive: true, force: true }); }
function mv(a, b) { rmrf(b); fs.renameSync(a, b); }

function parseArgs(argv) {
  const out = { cmd: null, outputs: 'outputs', expected: 'outputs/hashes.json', mode: 'auto', updateExpected: false };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--cmd') out.cmd = argv[++i];
    else if (a === '--outputs') out.outputs = argv[++i];
    else if (a === '--expected') out.expected = argv[++i];
    else if (a === '--mode') out.mode = argv[++i];
    else if (a === '--update-expected') out.updateExpected = true;
    else if (a === '-h' || a === '--help') out.help = true;
    else die(`Unknown arg: ${a}`);
  }
  return out;
}

function usage() {
  console.log([
    'reproducibility_check.js',
    '  --cmd "<pipeline command>"       (or set PIPELINE_CMD env var)',
    '  --outputs <dir>                  default: outputs',
    '  --expected <path>                default: outputs/hashes.json',
    '  --mode auto|compare|verify|both  default: auto (verify if expected exists, else compare)',
    '  --update-expected                write expected file from current outputs (after successful checks)'
  ].join('\n'));
}

function sha256File(fp) {
  const h = crypto.createHash('sha256');
  h.update(fs.readFileSync(fp));
  return h.digest('hex');
}

function listFilesRecursive(dir) {
  const files = [];
  function walk(d) {
    for (const ent of fs.readdirSync(d, { withFileTypes: true }).sort((a,b)=>a.name.localeCompare(b.name))) {
      const p = path.join(d, ent.name);
      if (ent.isDirectory()) walk(p);
      else if (ent.isFile()) files.push(p);
    }
  }
  walk(dir);
  return files;
}

function computeHashes(baseDir) {
  const base = path.resolve(baseDir);
  if (!exists(base)) die(`Outputs directory not found: ${base}`);
  const out = {};
  const files = listFilesRecursive(base);
  for (const fp of files) {
    const rel = path.relative(base, fp).split(path.sep).join('/');
    if (rel === 'hashes.json') continue;
    out[rel] = sha256File(fp);
  }
  return out;
}

function stableStringify(obj) {
  const keys = Object.keys(obj).sort();
  const o = {};
  for (const k of keys) o[k] = obj[k];
  return JSON.stringify(o, null, 2) + '\n';
}

function diffMaps(a, b) {
  const ka = new Set(Object.keys(a));
  const kb = new Set(Object.keys(b));
  const all = Array.from(new Set([...ka, ...kb])).sort();
  const diffs = [];
  for (const k of all) {
    if (!ka.has(k)) diffs.push(`Missing in A: ${k}`);
    else if (!kb.has(k)) diffs.push(`Missing in B: ${k}`);
    else if (a[k] !== b[k]) diffs.push(`Hash mismatch: ${k}\n  A=${a[k]}\n  B=${b[k]}`);
  }
  return diffs;
}

function runCmd(cmd) {
  execSync(cmd, { stdio: 'inherit', env: process.env, shell: true });
}

function main() {
  const args = parseArgs(process.argv);
  if (args.help) { usage(); process.exit(0); }
  const cmd = args.cmd || process.env.PIPELINE_CMD;
  if (!cmd) die('Missing pipeline command. Provide --cmd or set PIPELINE_CMD.');

  const root = process.cwd();
  const outputs = path.resolve(root, args.outputs);
  const expectedPath = path.resolve(root, args.expected);
  const run1Dir = path.resolve(root, args.outputs + '.__repro_run1');
  const run2Dir = path.resolve(root, args.outputs + '.__repro_run2');

  rmrf(run1Dir); rmrf(run2Dir);

  // Run 1
  rmrf(outputs);
  runCmd(cmd);
  if (!exists(outputs)) die(`Pipeline did not produce outputs dir: ${outputs}`);
  mv(outputs, run1Dir);

  // Run 2
  rmrf(outputs);
  runCmd(cmd);
  if (!exists(outputs)) die(`Pipeline did not produce outputs dir: ${outputs}`);
  mv(outputs, run2Dir);

  const h1 = computeHashes(run1Dir);
  const h2 = computeHashes(run2Dir);

  const mode = (args.mode === 'auto')
    ? (exists(expectedPath) ? 'both' : 'compare')
    : args.mode;

  if (mode === 'compare' || mode === 'both') {
    const diffs = diffMaps(h1, h2);
    if (diffs.length) {
      console.error('Reproducibility check failed: outputs differ between two runs.');
      console.error(diffs.slice(0, 50).join('\n'));
      if (diffs.length > 50) console.error(`...and ${diffs.length - 50} more differences`);
      die('NON_REPRODUCIBLE');
    }
  } else if (mode !== 'verify') {
    die(`Invalid --mode: ${args.mode}`);
  }

  // Restore outputs from run2 as canonical current outputs/
  mv(run2Dir, outputs);
  rmrf(run1Dir);

  const current = computeHashes(outputs);

  if ((mode === 'verify' || mode === 'both') && exists(expectedPath)) {
    let expected;
    try { expected = JSON.parse(fs.readFileSync(expectedPath, 'utf8')); }
    catch (e) { die(`Failed to read expected hashes: ${expectedPath}\n${e.message}`); }
    const diffs = diffMaps(expected, current);
    if (diffs.length) {
      console.error('Hash regression check failed: current outputs do not match expected hashes.json.');
      console.error(diffs.slice(0, 50).join('\n'));
      if (diffs.length > 50) console.error(`...and ${diffs.length - 50} more differences`);
      die('HASH_REGRESSION');
    }
  }

  if (args.updateExpected) {
    fs.mkdirSync(path.dirname(expectedPath), { recursive: true });
    fs.writeFileSync(expectedPath, stableStringify(current), 'utf8');
    console.error(`Updated expected hashes: ${path.relative(root, expectedPath)}`);
  }

  console.log('OK');
}

main();
