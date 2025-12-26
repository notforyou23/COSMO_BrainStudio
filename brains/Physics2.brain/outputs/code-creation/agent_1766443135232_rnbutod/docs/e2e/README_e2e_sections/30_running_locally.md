# Running locally

This section describes a repeatable way to run the end-to-end (E2E) suite on a developer machine, what “good” output looks like, and how to debug the most common failures.

## Quick start (most common)

From the repo root:

```bash
# (optional) create/activate a virtualenv
python -m venv .venv
source .venv/bin/activate  # on Windows: .venv\Scripts\activate

python -m pip install -U pip
python -m pip install -r docs/e2e/requirements-ci.txt

# run the full E2E suite
pytest -m e2e -q
```

## Selecting what to run

Run a single file:

```bash
pytest -m e2e tests/e2e/test_smoke.py -vv
```

Run a single test (substring match):

```bash
pytest -m e2e -k "login and happy_path" -vv
```

Run “smoke” only (if markers are defined in this repo):

```bash
pytest -m "e2e and smoke" -q
```

Re-run only failures from the last run:

```bash
pytest -m e2e --lf -vv
```

## Configuration and environment

E2E runs typically depend on config and/or environment variables (see the dedicated configuration section in this doc set). A common local pattern is:

```bash
export E2E_CONFIG_PATH=./configs/e2e.local.json
export E2E_ARTIFACTS_DIR=./artifacts/e2e
mkdir -p "$E2E_ARTIFACTS_DIR"

pytest -m e2e -vv
```

If your project uses a `.env` file, load it before running tests (or use your shell’s equivalent).

## Expected outputs

A successful run should include:

- Pytest summary with `passed` and exit code `0`
- An artifacts directory (logs, screenshots, traces, reports), if enabled
- No “collection” errors (those indicate import/config problems, not test failures)

Example summary:

```text
==================== 12 passed, 1 skipped in 03:41 ====================
```

If artifacts are enabled, you should see files created under your configured artifacts directory (for example, `artifacts/e2e/…`).

## Common flags (practical)

Pytest verbosity and logs:

```bash
pytest -m e2e -vv --log-cli-level=INFO
```

Stop early on the first failure:

```bash
pytest -m e2e --maxfail=1 -x
```

Show the slowest tests (useful for local tuning):

```bash
pytest -m e2e --durations=10
```

Disable capturing to see live stdout/stderr (useful when debugging hangs):

```bash
pytest -m e2e -s -vv
```

Parallel execution (requires `pytest-xdist`):

```bash
pytest -m e2e -n auto
```

## Troubleshooting

### 1) “ImportError / ModuleNotFoundError” during collection
Symptoms: errors appear before any tests run.

Fixes:
- Ensure the correct venv is activated and dependencies are installed.
- Reinstall with a clean environment if needed:
  ```bash
  python -m pip install -r docs/e2e/requirements-ci.txt --force-reinstall
  ```
- Verify you are running from the repository root.

### 2) Config validation / missing keys
Symptoms: tests fail quickly with a message about missing config/credentials/endpoints.

Fixes:
- Confirm your config path (for example, `E2E_CONFIG_PATH`) points to an existing file.
- Validate required keys match the configuration section.
- Ensure secrets are present in your local environment (but do not commit them).

### 3) Network/auth failures (401/403/5xx, timeouts)
Fixes:
- Confirm you are targeting the intended environment (local/staging/dev).
- Check VPN/proxy settings and DNS resolution.
- Retry once to rule out transient issues; if repeatable, capture logs/artifacts and file an issue.

### 4) Browser/UI failures (if applicable)
Fixes:
- Run headed to observe behavior (framework-specific), or increase logging.
- Ensure required system dependencies are installed (fonts, display libs, etc.).
- Collect traces/screenshots from the artifacts directory.

### 5) Flaky tests
Fixes:
- Re-run the failing test in isolation (`pytest -m e2e -k "<name>" -vv`).
- Use `--lf` to iterate quickly.
- If the failure is timing-related, prefer explicit waits over arbitrary sleeps; record timings via `--durations`.

## Notes for reproducibility

- Prefer running from a clean working tree to avoid local config drift.
- Record: git SHA, config file used, and artifacts directory when reporting failures.
- If CI passes but local fails, compare Python version and dependency versions (`python -V`, `pip freeze`).
