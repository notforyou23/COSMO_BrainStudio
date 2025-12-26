# /outputs Artifact Rules

This directory contains deterministic, reproducible run artifacts produced by the pipeline. The pipeline MUST create the required per-run files listed below on every run and MUST follow the naming, schema, and overwrite rules in this document.

## Required per-run files (always overwritten)
Each pipeline invocation writes these files (paths relative to repo root):
- `outputs/run_stamp.json`
- `outputs/run.log`
- `outputs/results.json`
- `outputs/figure.png`

These four files are considered the canonical “latest run” artifacts.

## Naming conventions
- Use lowercase snake_case for filenames.
- Prefer stable, human-readable names over timestamps in filenames.
- If optional extra artifacts are written, they MUST be namespaced/prefixed (e.g., `debug_*.json`) and documented by the pipeline; they MUST NOT replace or rename the required files above.

## Overwrite policy (deterministic “latest run”)
- The pipeline overwrites the required per-run files on every run.
- The pipeline MUST NOT append to `outputs/run.log`; it is rewritten each run to keep log contents deterministic.
- Partial writes MUST be avoided: write to a temporary file in the same directory and rename atomically when practical.

## Determinism rules
The pipeline is expected to produce byte-for-byte identical artifacts when inputs and environment are unchanged.
- Fixed random seed(s): all PRNGs used (e.g., `random`, `numpy`) MUST be seeded from a single documented seed value.
- Stable ordering: any iteration over sets/maps MUST be sorted; results MUST not depend on hash iteration order.
- Stable numeric formatting: JSON floats should be emitted consistently (default Python `json` is acceptable if inputs are deterministic).
- Stable timestamps: a real wall-clock timestamp may be recorded for traceability, but it MUST NOT affect computed results or plotting. Prefer recording both `created_utc` (trace) and a deterministic `run_id` derived from inputs/config.
- Plot determinism: fixed figure size, DPI, style, and any sampling must be seeded. Avoid embedding non-deterministic metadata (e.g., Matplotlib “CreationTime”) when possible.

## JSON serialization rules
- UTF-8 encoding.
- Newline at EOF.
- `json.dump(..., sort_keys=True, indent=2)` (or equivalent) so key order and formatting are stable.
- Only JSON-serializable primitives: object, array, string, number, boolean, null.
- Schema versioning: include a `schema_version` integer at the top level for each JSON artifact.

## Schemas

### outputs/run_stamp.json
Purpose: Identifies the run and captures configuration and provenance without affecting results.
Top-level object:
- `schema_version` (int, required): currently `1`.
- `run_id` (string, required): deterministic identifier (e.g., hash of config/inputs).
- `created_utc` (string, required): RFC3339/ISO-8601 UTC timestamp (trace only).
- `seed` (int, required): global seed used for the run.
- `command` (string, optional): executed CLI command.
- `inputs` (object, required): stable description of inputs (paths, parameters); keys must be stable/sorted.
- `environment` (object, optional): python version, platform; informational only.

### outputs/results.json
Purpose: Machine-readable final results used for downstream automation and plotting.
Top-level object:
- `schema_version` (int, required): currently `1`.
- `run_id` (string, required): must match `run_stamp.json`.
- `summary` (object, required): high-level metrics (scalars).
- `series` (object, optional): arrays/vectors used for plots; each array must have consistent length.
- `parameters` (object, required): effective parameters used for computation.
- `warnings` (array of strings, optional): deterministic warnings emitted during the run.

### outputs/run.log
Purpose: Human-readable log of the run with deterministic structure.
- Text file, UTF-8.
- Rewritten each run (no append).
- Recommended format: line-oriented `KEY=VALUE` or a structured, consistent prefix per line (e.g., `INFO ...`).
- If timestamps are included, they should be either omitted or fixed-format UTC and must not affect results.

### outputs/figure.png
Purpose: Deterministic visualization derived solely from `results.json`.
- PNG, fixed dimensions and DPI.
- Do not include non-deterministic metadata when possible.
- The data used for plotting MUST come from `results.json` (or the same deterministic in-memory structure that is serialized there).

## Validation expectations
- The pipeline SHOULD validate that required files exist after execution.
- JSON artifacts SHOULD be validated against the schemas above (at minimum: required keys, types, `schema_version`, matching `run_id` across artifacts).
- If validation fails, the pipeline should exit non-zero and still leave a readable `run.log` explaining the failure.
