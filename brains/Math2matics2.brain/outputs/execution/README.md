# Deterministic CLI Tool

This project exposes a single deterministic CLI entrypoint that runs a canonical pipeline and produces fixed output artifacts for CI verification.

## Quickstart

From the repository root:

- Run:
  - `python -m src.run`
  - or `python src/run.py`

- Optional flags (if implemented):
  - `--seed <int>`: base RNG seed (default is fixed by the tool)
  - `--outputs <path>`: output directory (default: `./outputs`)

The tool will create/update:
- `./outputs/results.json`
- `./outputs/figure.png`
- `./outputs/hashes.json`

## Determinism guarantees

The entrypoint is designed to be bit-for-bit reproducible given the same:
- code + dependencies (pin versions for strict reproducibility),
- OS/CPU/Python runtime (CI should standardize these),
- CLI arguments and environment variables.

At startup, the tool sets RNG seeds for:
- Python `random`
- NumPy
- (Optional) PyTorch, if installed

It also enables deterministic settings where supported (e.g., torch deterministic algorithms). The pipeline is implemented as pure functions where possible to avoid hidden global state.

### What can break determinism?

Common sources of non-determinism:
- differing library versions (NumPy/Matplotlib/Pillow/Torch),
- different font availability / rendering backends (affects PNG bytes),
- parallelism / BLAS differences,
- locale/timezone differences (avoid timestamps in outputs).

This project addresses these by:
- fixed seed(s),
- fixed output schema and stable JSON serialization,
- fixed Matplotlib settings (recommended: explicit figure size/DPI, avoid timestamps/metadata where possible),
- hashing artifacts for verification.

## Output artifacts (fixed locations)

All outputs are written under `./outputs/` relative to the working directory (unless overridden by the CLI).

### `outputs/results.json` (fixed schema)

JSON object with stable keys and types:

- `schema_version` (string): version of the results schema (e.g., `"1"`).
- `seed` (integer): base seed used for the run.
- `pipeline` (object):
  - `name` (string): canonical pipeline identifier.
  - `parameters` (object): pipeline parameters (numbers/strings/booleans; no timestamps).
- `metrics` (object): computed scalar metrics (float/int), keyed by metric name.
- `artifacts` (object):
  - `results_json` (string): relative path, always `"outputs/results.json"`.
  - `figure_png` (string): relative path, always `"outputs/figure.png"`.
  - `hashes_json` (string): relative path, always `"outputs/hashes.json"`.

Notes:
- JSON should be serialized deterministically (sorted keys, no NaN/Infinity, consistent float formatting where applicable).
- No run time, hostname, git hash, or other environment-dependent fields should be included.

### `outputs/figure.png`

A single PNG produced by the pipeline (e.g., plot of generated/processed data). For determinism:
- use fixed figsize and dpi,
- use deterministic data ordering,
- avoid embedding timestamps or variable metadata.

### `outputs/hashes.json` (fixed schema)

JSON object mapping artifact file names to SHA256 hex digests:

- `schema_version` (string): version of the hash schema (e.g., `"1"`).
- `sha256` (object):
  - `outputs/results.json` (string): 64-char hex SHA256
  - `outputs/figure.png` (string): 64-char hex SHA256
  - `outputs/hashes.json` (string): 64-char hex SHA256 (hash of the file contents as written)

The hash file exists to support CI/CD determinism checks:
- run the CLI,
- compute/compare expected hashes,
- fail the build if hashes differ.

## CI/CD usage pattern

Typical CI job steps:
1. Install dependencies (pinned).
2. Run `python -m src.run` in a clean workspace.
3. Upload `outputs/` as build artifacts.
4. Verify `outputs/hashes.json` matches a committed/expected reference (or compare to previous run).

If you update the pipeline or plotting, hashes will change; update the expected hashes as part of the change with an explanation in the PR.
