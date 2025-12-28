# Goal 1 — Simulation Results Pack (Required Contents + Acceptance Criteria)

## Purpose
This document defines the **required contents**, **metadata**, and **validation checklist** for the Goal 1 simulation results pack so results are reproducible, auditable, and comparable across runs.

## Pack scope (what must be included)
A complete results pack represents **one simulation campaign** (one or more runs) for a defined model + configuration set and must be sufficient for a reviewer to:
1) understand intent and assumptions, 2) reproduce the run, and 3) verify results integrity.

## Directory layout (recommended)
Place the campaign under a single folder (example name):
- `outputs/sim/goal_1/<campaign_id>/`

Recommended subfolders (use what applies; omit empty):
- `inputs/` (configs, scenario definitions, parameter sets)
- `artifacts/` (compiled binaries, exported model snapshots, generated code)
- `results/` (primary outputs: time series, KPIs, events)
- `plots/` (figures derived from results)
- `logs/` (stdout/stderr, solver logs, warnings)
- `reports/` (human-readable summary; this can include PDFs/HTML)
- `provenance/` (environment capture, dependency lockfiles, checksums)

## Required files (minimum set)
Each campaign must include the following files at the campaign root (or in the specified subfolder).

### 1) Manifest (required)
File: `manifest.json`  
Must contain (keys required unless marked optional):
- `campaign_id` (string; stable identifier)
- `created_utc` (ISO-8601 UTC timestamp)
- `owner` (name/email or team identifier)
- `model`:
  - `name`
  - `version` (semantic or commit hash)
  - `source` (repo URL or local path reference)
- `simulator`:
  - `name`
  - `version`
  - `solver` (if applicable)
- `scenario`:
  - `name`
  - `description`
- `run_matrix` (array of runs):
  - `run_id`, `seed` (if applicable), `config_ref`, `command_ref`, `outputs_ref`
- `outputs`:
  - `primary_results` (list of file paths)
  - `plots` (list of file paths, optional)
  - `reports` (list of file paths, optional)
- `metrics` (dictionary of key KPIs; may be empty but key must exist)
- `hardware` (CPU/GPU info if relevant; minimal text acceptable)
- `notes` (optional)

### 2) Reproduction instructions (required)
File: `REPRODUCE.md`  
Must include:
- prerequisites (OS/tools)
- exact command(s) to run (copy/paste ready)
- where outputs will be written
- expected runtime order-of-magnitude
- how to confirm success (which files/KPIs to check)

### 3) Inputs/configuration capture (required)
At least one of the following must exist:
- `inputs/` directory containing the exact configs used (preferred), OR
- a single file: `inputs_bundle.(zip|tar.gz)` containing those configs.

Additionally, include one of:
- `command.sh` (exact CLI invocation), OR
- `command.json` (structured command + args + working directory)

### 4) Primary results (required)
At least one machine-readable primary output file, referenced in `manifest.json`, such as:
- `results/results.csv` (tabular time series or KPIs)
- `results/results.parquet`
- `results/results.json`
- `results/events.ndjson`

Primary results must include enough fields to evaluate the campaign’s headline KPIs.

### 5) Run logs (required)
At least one log file:
- `logs/run.log` (or equivalent)
Must include:
- start/end timestamps
- warnings/errors (if any)
- simulator version banner (or equivalent evidence)

### 6) Integrity metadata (required)
File: `provenance/checksums.sha256`  
Must contain SHA-256 checksums for all files referenced in `manifest.json` outputs and for `manifest.json` itself.

## Optional but strongly recommended
- `provenance/environment.txt` (OS, Python version, key libs)
- `provenance/requirements.txt` or `poetry.lock` / `uv.lock`
- `plots/` (PNG/SVG) for key metrics
- `reports/summary.md` (1–2 pages: intent, setup, results, interpretation)
- `results/derived_kpis.json` (computed KPIs with units)

## Result quality rules (minimum)
- Units must be explicit for all reported KPIs (in file headers, schema, or a companion metadata file).
- Any randomness must be controlled via documented seeds.
- If a run fails, the pack must still include logs and a clear failure status in `manifest.json` (do not omit failures).

## Validation checklist (acceptance criteria)
A Goal 1 simulation results pack is **ACCEPTED** only if all items below are true:

### A) Completeness
- [ ] `manifest.json` exists and includes all required keys.
- [ ] `REPRODUCE.md` exists and provides exact run commands and verification steps.
- [ ] Inputs/configs used are present and immutable (directory or bundle).
- [ ] At least one primary results file exists and is referenced in the manifest.
- [ ] At least one run log exists.

### B) Reproducibility
- [ ] A reviewer can run the documented command(s) without guessing missing parameters.
- [ ] Versions (model + simulator) are recorded.
- [ ] Seeds are recorded for stochastic simulations (or explicitly marked not applicable).

### C) Integrity & traceability
- [ ] `provenance/checksums.sha256` exists and covers all referenced outputs.
- [ ] Paths referenced in `manifest.json` resolve within the campaign directory.
- [ ] Each `run_id` has a clear mapping to its config and outputs.

### D) Result sanity
- [ ] Headline KPIs are present in `manifest.json` (`metrics` populated or explicitly empty with justification in `notes`).
- [ ] Logs do not show unhandled exceptions; if failures exist they are clearly marked and explained.
- [ ] Derived figures/plots (if present) correspond to the primary results (same run ids/time windows).

## Reviewer sign-off (fill in during review)
- Reviewer:
- Date (UTC):
- Campaign ID:
- Verdict: ACCEPT / REJECT
- Notes:
