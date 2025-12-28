# One-command Build Runner

This project provides a single CLI entrypoint to run the repository’s verification steps in a fixed order, writing all logs and generated outputs into `_build/`, and failing fast on the first error.

## What it runs (sequential, fail-fast)

1. **Artifact gate**: verifies expected artifacts are present/consistent.
2. **Taxonomy validation**: validates taxonomy files (schemas, structure, constraints).
3. **Toy meta-analysis demo**: runs an end-to-end demo pipeline to confirm the meta-analysis “starter kit” works.

If any step exits non-zero, the runner stops immediately and the overall command exits non-zero.

## Prerequisites

- Python 3.10+ recommended.
- Run from the repository root (so relative paths resolve correctly).
- Install project dependencies (if the repo uses a venv, activate it first). Example:
  - `python -m pip install -r requirements.txt` (or your repo’s equivalent)

## Quick start

Run the full build:
- `python scripts/build_runner.py`

Common options (if supported by your version):
- Show help: `python scripts/build_runner.py -h`
- Choose build directory: `python scripts/build_runner.py --build-dir _build`
- Clean build outputs first: `python scripts/build_runner.py --clean`
- Run a subset of steps: `python scripts/build_runner.py --steps artifact_gate taxonomy_validation meta_analysis_demo`

## Outputs and logs (`_build/`)

The runner creates (or reuses) `_build/` in the repo root and writes:
- Step logs (stdout/stderr tee’d to console and files), typically under:
  - `_build/logs/<timestamp>_<step_name>.log`
- Any step-produced artifacts/exports (as emitted by the invoked tools), typically under:
  - `_build/outputs/` (or a step-specific subfolder)

Exact filenames may vary by implementation, but **everything should land under `_build/`**.

## Exit codes

- `0`: all steps succeeded
- `!= 0`: at least one step failed; the first failing step’s exit code is propagated (or a runner-defined non-zero code)

## Troubleshooting

### “Command not found” / missing module / import errors
- Ensure you are using the intended Python interpreter:
  - `python -c "import sys; print(sys.executable)"`
- Ensure dependencies are installed in that environment.

### A step fails, but I need more detail
- Open the corresponding log file in `_build/logs/` for full stdout/stderr.
- Re-run a single step (if supported) to iterate faster:
  - `python scripts/build_runner.py --steps taxonomy_validation`

### `_build/` contains stale outputs
- Clean and re-run:
  - `python scripts/build_runner.py --clean`

### Running from the wrong directory
- The runner expects to be launched from the repo root. If you ran it elsewhere, `cd` to the root and try again.

## CI usage

In CI, run exactly the same command as locally to avoid drift:
- `python scripts/build_runner.py`

Because logs are written to `_build/`, CI can archive that directory as a build artifact for debugging.
