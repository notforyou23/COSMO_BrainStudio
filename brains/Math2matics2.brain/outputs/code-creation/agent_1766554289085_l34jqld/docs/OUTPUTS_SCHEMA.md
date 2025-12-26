# Canonical Outputs Schema (Enforced)

This project enforces a single, canonical outputs layout and a fixed `outputs/results.json` schema. The pipeline entrypoint `python scripts/run_pipeline.py` must write these outputs and validate them before exiting.

## Canonical outputs layout

All runs write to the following paths (relative to the project root / current working directory):

- `outputs/`
  - `results.json` (required) — machine-readable run summary (fixed keys, deterministic formatting)
  - `figure.png` (required) — primary figure artifact
  - *(optional, allowed)* additional files may be written under `outputs/`, but the two files above are always required.

Notes:
- The pipeline must create the `outputs/` directory if it does not exist.
- `outputs/results.json` must reference artifacts using paths relative to the project root (e.g., `outputs/figure.png`).
## `outputs/results.json` schema (fixed keys)

`results.json` is a single JSON object with the following **fixed top-level keys**. No keys may be omitted. Extra keys are not allowed.

Top-level keys and types:

- `schema_version` (string)  
  Version of this outputs schema. Example: `"1.0"`.

- `run_id` (string)  
  Stable identifier for the run (e.g., UUID or timestamp-based). Used for traceability.

- `status` (string)  
  One of: `"success"` or `"error"`.

- `seed` (integer)  
  The single canonical RNG seed used for the run. Always written even if the user did not provide one (the pipeline chooses one and records it).

- `started_at_utc` (string)  
  ISO-8601 UTC timestamp for run start. Example: `"2025-12-24T01:23:45Z"`.

- `finished_at_utc` (string)  
  ISO-8601 UTC timestamp for run end.

- `duration_seconds` (number)  
  Wall-clock duration in seconds (may be float).

- `metrics` (object)  
  JSON object mapping metric names (strings) to JSON numbers/strings/booleans/null. Must exist (may be `{}`).

- `artifacts` (object)  
  Artifact paths produced by the run. Must exist with the keys below.

- `warnings` (array)  
  List of warning strings. Must exist (may be `[]`).

- `errors` (array)  
  List of error strings. Must exist (may be `[]`). If `status == "error"`, this should be non-empty.

### `artifacts` object

`artifacts` must contain exactly these keys:

- `results_json` (string) — must equal `"outputs/results.json"`
- `figure_png` (string) — must equal `"outputs/figure.png"`
## Deterministic writing requirements

The pipeline must write `outputs/results.json` deterministically:
- UTF-8 encoding
- Unix newlines (`\n`)
- Stable key ordering (canonical order matching the fixed key list above)
- Stable formatting (no non-deterministic whitespace; trailing newline required)

`outputs/figure.png` must be overwritten each run. When the same inputs and the same `seed` are used, the produced outputs should be reproducible to the extent allowed by the underlying libraries and platform.

## Output validation (must pass before exit)

Before the pipeline exits, it validates:
1. `outputs/results.json` exists and is valid JSON.
2. The JSON object has exactly the fixed keys listed above and the correct types.
3. `artifacts.results_json == "outputs/results.json"` and `artifacts.figure_png == "outputs/figure.png"`.
4. `outputs/figure.png` exists and is a non-empty file.

If validation fails, the pipeline must exit with a non-zero status and record a failure in `results.json` when possible.
## Unified seed control (single seed propagated)

The pipeline entrypoint accepts a single seed and propagates it across common RNGs so downstream steps share one deterministic source of randomness.

Seed propagation includes:
- Python `random`
- NumPy RNG (if NumPy is installed)
- Other libraries (e.g., torch) when available; best-effort without adding hard dependencies.

The seed used for the run is always recorded in `outputs/results.json` under the `seed` key.

## How to run (deterministic)

From the project root:

- Deterministic run (recommended for CI):
  - `python scripts/run_pipeline.py --seed 123`

- Non-deterministic run (seed chosen by pipeline, then recorded):
  - `python scripts/run_pipeline.py`

The run will always produce:
- `outputs/results.json`
- `outputs/figure.png`
