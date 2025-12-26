# outputs/ directory: test-run artifacts

This repository includes a “test-capture” step that runs the test suite and writes canonical, reproducible artifacts under `outputs/`.

The canonical artifacts are:

- `outputs/pytest_output.txt`: full `pytest` console output (combined stdout/stderr) from the run.
- `outputs/run_metadata.json`: structured metadata about the run (machine/CI context, timing, command, exit code, and artifact paths).

An index of the directory is maintained in `outputs/index.md`, which should link back to this document (`outputs/README.md`).
## Run locally

Prerequisites:
- Python environment with project dependencies installed (including `pytest`).
- Run from the repository root.

Command:

```bash
python scripts/run_tests_and_capture.py
```

Expected results:
- Exit code mirrors the underlying `pytest` exit code (0 = success; non-zero = failures/errors).
- `outputs/pytest_output.txt` is created/overwritten with the full console log.
- `outputs/run_metadata.json` is created/overwritten with structured metadata.

Tip: to keep artifacts from a previous run, copy them elsewhere before re-running.
## Run in CI

Add a CI step that:
1. Installs dependencies
2. Runs the capture script
3. Uploads the `outputs/` directory as an artifact (or at minimum the two canonical files)

Example (generic shell step):

```bash
python -m pip install -r requirements.txt
python scripts/run_tests_and_capture.py
# then archive/upload: outputs/pytest_output.txt and outputs/run_metadata.json
```

Recommended: always upload artifacts even when tests fail, so the failing log and metadata are preserved.
## Artifact details

### `outputs/pytest_output.txt`
A plain-text, line-for-line capture of the `pytest` run output, intended for:
- Debugging failures (tracebacks, captured output, summary)
- Auditing what was executed (plugins, collected tests, warnings)

Notes:
- The file is overwritten on each run.
- Content is unstructured by design; use `run_metadata.json` for machine-readable fields.

### `outputs/run_metadata.json`
A JSON document intended for programmatic consumption (dashboards, trend tracking, CI summaries).
While fields may evolve, it is expected to include (directly or nested):
- `timestamp` / `started_at` and `finished_at` (or a `duration_seconds`)
- `command` used to invoke pytest (or the capture script)
- `cwd` / repository context
- `exit_code` from pytest
- paths to produced artifacts (e.g., `outputs/pytest_output.txt`)
- CI indicators when available (e.g., `ci=true`, provider name, run/job identifiers)

How to use:
- Prefer `exit_code` and timestamps for automation.
- Use `pytest_output.txt` as the authoritative human-readable log referenced by the metadata.
## Relationship to `outputs/index.md`

`outputs/index.md` is the directory landing page. It should:
- Link to this file (`outputs/README.md`) for instructions and artifact definitions
- Summarize the canonical artifacts produced by the test-capture step

When updating filenames or adding new canonical artifacts, update both `outputs/index.md` and this README accordingly.
