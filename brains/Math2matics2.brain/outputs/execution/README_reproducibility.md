# Reproducibility & Artifact Hash Checks

This project includes a reproducibility gate intended for both local development and CI/CD:

1) Run the pipeline twice from a clean state.
2) Compute SHA256 hashes for every artifact under `./outputs/`.
3) Fail if (a) run-to-run hashes differ or (b) hashes differ from the repository’s expected `outputs/hashes.json` (regression check).

The goal is to ensure the pipeline is deterministic and that any intentional output changes are explicitly reviewed and recorded.

## What gets checked

- All files under `outputs/` (recursively) are enumerated deterministically (stable ordering).
- Hashes are computed over file bytes using SHA256.
- Hashes are compared:
  - **Run A vs Run B** (reproducibility).
  - **Run A vs `outputs/hashes.json`** (regression / “expected outputs” contract), when enabled.

## Local usage

### 1) Run the full reproducibility check

Use the Make target (recommended) or call the Node script directly.

- Make:
  - `make reproducibility` (or similarly named target in this repo)

- Direct:
  - `node scripts/reproducibility_check.js`

Typical behavior:
- The script runs the pipeline twice (often with cleanup between runs), then compares output hashes.
- Exits non-zero on any mismatch (suitable for CI).

### 2) Generate or update expected hashes (`outputs/hashes.json`)

If you intentionally changed pipeline outputs, update the expected hash file:

- `node scripts/hash_outputs.js`

This regenerates `outputs/hashes.json` from the current `outputs/` contents. Commit the updated file so CI can enforce the new expected outputs.

## CI/CD usage

CI should:
1) Check out the repo.
2) Install dependencies.
3) Run the pipeline (if not already done inside the reproducibility script).
4) Run `node scripts/reproducibility_check.js`.
5) Fail the workflow if any mismatch occurs.

A typical GitHub Actions workflow will be located at:
- `.github/workflows/reproducibility.yml`

## How to interpret failures

### A) Run-to-run mismatch (non-determinism)

Symptoms:
- Hashes differ between the two consecutive runs.
- CI/local run fails even if `outputs/hashes.json` is unchanged.

Common causes and fixes:
- Randomness: seed all RNGs (JS, Python, libraries) and persist seeds in config.
- Timestamps: avoid embedding build times in artifacts; sort inputs; strip non-deterministic metadata.
- Unstable ordering: sort directory listings, keys, and records before writing outputs.
- Parallelism/races: ensure deterministic scheduling or post-sort results.
- Environment sensitivity: normalize locale/timezone, line endings, floating-point formatting.

Diagnosis tips:
- Compare the two run directories / hash listings if the script emits them.
- Re-run locally with verbose logging enabled by the script (if supported).
- Narrow down to the first differing file and inspect it:
  - Is it purely metadata or truly different content?
  - Does it include timestamps, GUIDs, or non-stable ordering?

### B) Expected-hash mismatch (regression contract)

Symptoms:
- Run-to-run comparison passes, but hashes differ from `outputs/hashes.json`.

Meaning:
- The pipeline is deterministic, but outputs changed relative to the committed baseline.

What to do:
- If change is expected: run `node scripts/hash_outputs.js`, review the diff, commit updated `outputs/hashes.json`.
- If change is unexpected: treat as a regression; inspect the changed artifacts and recent code/config changes.

## Best practices

- Keep `outputs/` contents stable and minimal: only deterministic artifacts that represent the pipeline result.
- Avoid including machine-specific paths, hostnames, temp directories, and timestamps in outputs.
- Prefer canonical serialization (stable JSON key order, consistent formatting, deterministic compression if used).
- Document any intentional output changes in the commit that updates `outputs/hashes.json`.

## Notes

- `outputs/hashes.json` is the canonical baseline for regression checks.
- The reproducibility check is designed to be strict: if it flakes, fix determinism rather than weakening the gate.
