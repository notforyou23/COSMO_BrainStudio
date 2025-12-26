# Project Roadmap (v1)

This roadmap tracks delivery of CI/CD-ready run automation and traceability artifacts (logs, run stamps, and results indexing).

## Deliverables status (CI/CD traceability)

### Completed (Stage 1)
- [x] **Test-and-log runner**: `scripts/run_tests_and_capture_log.py`
  - Captures stdout/stderr to timestamped logs under `outputs/logs/`
  - Writes `run_stamp.json` per run
  - Updates the central run registry: `outputs/index.md`
  - Evidence / entrypoint:
    - Index: `outputs/index.md`
    - Logs directory: `outputs/logs/`
    - Run stamp: `outputs/run_stamp.json` (or as referenced by `outputs/index.md`)
    - Results artifacts: see “Results” section in `outputs/index.md`

- [x] **Pipeline runner**: `scripts/run_pipeline.py`
  - Executes the configurable pipeline entrypoint and captures stdout/stderr
  - Writes `run_stamp.json` per run
  - Updates `outputs/index.md` deterministically to include run log(s) and discovered results files
  - Evidence / entrypoint:
    - Index: `outputs/index.md`
    - Logs directory: `outputs/logs/`
    - Run stamp: `outputs/run_stamp.json` (or as referenced by `outputs/index.md`)
    - Results artifacts: see “Results” section in `outputs/index.md`

- [x] **Shared logging/index utilities**: `scripts/_log_index_utils.py`
  - Shared helpers for timestamping, log capture, result discovery, and deterministic `outputs/index.md` updates

- [x] **Central run index**: `outputs/index.md`
  - Single source of truth for recent + historical run logs and artifacts
  - Links to logs under `outputs/logs/`, plus `run_stamp.json` and result files

## How to verify quickly
1. Run tests via the runner and confirm a new log appears under `outputs/logs/` and a corresponding entry appears in `outputs/index.md`.
2. Run the pipeline via the runner and confirm the same: new log entry + any produced results listed in `outputs/index.md`.
3. Confirm `run_stamp.json` is present and referenced from `outputs/index.md`.

## Notes / conventions
- Logs are timestamped and stored under `outputs/logs/` for CI/CD auditability.
- `outputs/index.md` is the authoritative ledger; if specific filenames differ by timestamp, follow the links in the index.
