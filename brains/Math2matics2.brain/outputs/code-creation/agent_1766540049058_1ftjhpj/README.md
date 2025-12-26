# Minimal canonical outputs pipeline

This repo contains a tiny, runnable pipeline that produces a canonical `/outputs` folder on every run:
1) an outputs index, 2) per-run evidence, and 3) at least one domain artifact stub. It also re-attempts a previously blocked “survey” step while recording the outcome into run evidence.

## Quickstart (local)

Prereqs: Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -U pip
# If requirements exist in your environment, install them; otherwise stdlib is sufficient.
python -m src.cli run
```

Optional flags (see `--help`):
```bash
python -m src.cli --help
python -m src.cli run --outputs-dir outputs
```

## What a run produces (canonical artifacts)

All artifacts are written under the outputs directory (default: `./outputs`). Paths are deterministic and discoverable via the index.

### 1) Outputs index (cross-run registry)

- **Path:** `outputs/index.json`
- **Purpose:** Registry of runs and pointers to their evidence/artifacts.
- **Typical contents:** schema/version, `latest_run_id`, and a list/map of runs with timestamps and relative paths.

### 2) Run evidence (per-run provenance + results)

- **Path:** `outputs/runs/<run_id>/run_evidence.json`
- **Purpose:** Single source of truth for “what happened” in a run: start/end time, parameters, environment info, step statuses, errors, and the survey retry result.
- **Notes:** The survey retry logic is expected to write a structured result (success/failure, reason, and any payload) into this file so CI and humans can audit the run.

### 3) Domain artifact stub (example deliverable)

- **Path (example):** `outputs/runs/<run_id>/artifacts/domain_artifact_stub.json`
- **Purpose:** Demonstrates how domain outputs should be emitted in a stable location with metadata.
- **Typical contents:** minimal metadata (run id, created time, content type) plus an empty/seed structure representing the domain deliverable.

## Re-attempted survey task (why it’s here)

The pipeline includes a “survey retry” step that previously failed due to missing canonical artifacts.
Now it:
- reads/writes via the canonical paths above,
- records attempt count and outcome in `run_evidence.json`,
- and ensures artifacts exist even when the survey cannot complete (so runs remain auditable).

## CI/CD usage

A minimal CI job should:
1) set up Python,
2) run the pipeline once,
3) upload `outputs/` as an artifact.

Example (GitHub Actions):

```yaml
name: pipeline
on: [push, pull_request]
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: python -m pip install -U pip
      - run: python -m src.cli run
      - uses: actions/upload-artifact@v4
        with:
          name: outputs
          path: outputs
```

In other CI systems, the same pattern applies: run `python -m src.cli run` and persist the `outputs/` directory for later inspection.

## How to inspect results

After a run, start with:
- `outputs/index.json` to find the latest run id,
- then open `outputs/runs/<run_id>/run_evidence.json` for step-by-step results,
- and check `outputs/runs/<run_id>/artifacts/` for domain artifacts produced by the pipeline.
