#!/usr/bin/env node
'use strict';

const fs = require('fs');
const fsp = fs.promises;
const path = require('path');
const crypto = require('crypto');

function toPosix(p) {
  return p.split(path.sep).join('/');
}

async function listFilesRecursive(rootDir) {
  const out = [];
  async function walk(dir) {
    const entries = await fsp.readdir(dir, { withFileTypes: true });
    entries.sort((a, b) => a.name.localeCompare(b.name, 'en'));
    for (const ent of entries) {
      const full = path.join(dir, ent.name);
      if (ent.isDirectory()) {
        await walk(full);
      } else if (ent.isFile()) {
        out.push(full);
      }
    }
  }
  await walk(rootDir);
  return out;
}

async function sha256File(filePath) {
  return new Promise((resolve, reject) => {
    const h = crypto.createHash('sha256');
    const s = fs.createReadStream(filePath);
    s.on('error', reject);
    s.on('data', (chunk) => h.update(chunk));
    s.on('end', () => resolve(h.digest('hex')));
  });
}

async function main() {
  const cwd = process.cwd();
  const outputsDir = path.resolve(cwd, process.argv[2] || 'outputs');
  const outFile = path.resolve(cwd, process.argv[3] || path.join('outputs', 'hashes.json'));
  const outFileRelToOutputs = toPosix(path.relative(outputsDir, outFile));

  let st;
  try {
    st = await fsp.stat(outputsDir);
  } catch (e) {
    console.error(`[hash_outputs] outputs directory not found: ${outputsDir}`);
    process.exit(2);
  }
  if (!st.isDirectory()) {
    console.error(`[hash_outputs] not a directory: ${outputsDir}`);
    process.exit(2);
  }

  const files = await listFilesRecursive(outputsDir);
  const mapping = {};
  for (const abs of files) {
    const rel = toPosix(path.relative(outputsDir, abs));
    if (!rel || rel === '.' || rel === outFileRelToOutputs) continue;
    const digest = await sha256File(abs);
    mapping[rel] = digest;
  }

  const sorted = {};
  for (const k of Object.keys(mapping).sort((a, b) => a.localeCompare(b, 'en'))) {
    sorted[k] = mapping[k];
  }

  await fsp.mkdir(path.dirname(outFile), { recursive: true });
  const jsonText = JSON.stringify(sorted, null, 2) + '\n';
  await fsp.writeFile(outFile, jsonText, 'utf8');
  console.log(`[hash_outputs] wrote ${Object.keys(sorted).length} hashes to ${path.relative(cwd, outFile)}`);
}

main().catch((err) => {
  console.error('[hash_outputs] error:', err && err.stack ? err.stack : String(err));
  process.exit(1);
});
