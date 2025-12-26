# Deterministic output generator

This project contains a minimal, deterministic entrypoint script under `outputs/src/` that generates reproducible artifacts and a run log under `outputs/` on every execution.

## How to run

From the repository root (or from `/mnt/data` in Code Interpreter):

```bash
python outputs/src/main.py
```

Optional flags (see `--help` for the authoritative list):

```bash
python outputs/src/main.py --seed 0 --outdir outputs
```

## Deterministic behavior

The script is designed to be reproducible given the same:
- code and pinned dependencies (`outputs/src/requirements.txt`)
- input arguments (including `--seed`)
- Python version / platform (recorded in the run log)

It uses a fixed default seed and records the effective seed in the run log; providing `--seed` overrides the default.

## Produced artifacts

Each run writes its outputs beneath the specified output directory (default: `outputs/`). Artifacts are written in a stable, deterministic format so repeated runs with the same inputs produce identical files.

Typical structure:

- `outputs/artifacts/` — generated deterministic artifacts (files may be overwritten or versioned depending on arguments)
- `outputs/logs/` — run logs for traceability

## Run logs

Every execution writes a JSON run log under:

- `outputs/logs/run_YYYYMMDD_HHMMSSZ.json` (or similar)

The run log captures:
- command-line arguments and resolved output paths
- effective seed and any deterministic configuration
- Python/runtime/platform information
- hashes or summaries of produced artifacts (when applicable)

This makes it possible to audit and reproduce a run by rerunning the same command with the recorded seed and environment.
