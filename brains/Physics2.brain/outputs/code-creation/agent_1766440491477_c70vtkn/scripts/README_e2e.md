# End-to-end (E2E) pipeline runner

This repo exposes **one** command to run the full pipeline end-to-end, capture logs, and prepare artifacts for CI upload: **`make e2e`**.

## Local usage

### Prereqs
- Python 3 (uses the repo's dependencies/venv as defined by the project)
- `make` available

### Run
```bash
make e2e
```

### Outputs (local)
`make e2e` runs `scripts/e2e.py` (the orchestrator). By default it writes a run directory:

- `artifacts/e2e/<run_id>/`
  - `e2e.log` (combined stdout/stderr)
  - `summary.json` (structured stage results: status, timings, exit codes)
  - `manifest.json` (deterministic list of produced files + checksums)
  - `failure_summary.md` (human-readable failure report when something fails)
  - `logs/` (per-stage logs, when available)
  - `results/` (pipeline outputs, when available)

You can control where artifacts go:
```bash
ARTIFACT_DIR=artifacts/e2e make e2e
```

## CI usage (GitHub Actions)

The workflow `.github/workflows/e2e.yml` runs **exactly the same command**:
```yaml
- run: make e2e
```

### Artifact upload
The workflow uploads the full run directory (e.g. `artifacts/e2e/<run_id>/`) using `actions/upload-artifact`.
This makes failures debuggable without rerunning locally; download the artifact and inspect `failure_summary.md`,
`summary.json`, and `e2e.log`.

### Exit behavior
- If all stages succeed: `make e2e` exits `0`.
- If any stage fails: `make e2e` exits non-zero and still writes artifacts/logs up to the point of failure.

## How logging and artifacts are produced

- `scripts/e2e.py` runs each pipeline stage as a subprocess, capturing **stdout/stderr**, exit code, and duration.
- Logs are written both as:
  - a consolidated `e2e.log`
  - per-stage logs under `logs/`
- `scripts/artifacts.py` produces:
  - a deterministic `manifest.json` so runs can be compared
  - optional redaction of common secrets before packaging/upload (e.g. tokens in env/output)

## Automatic failure issue creation (and deduplication)

In CI, when `make e2e` fails, the workflow triggers issue creation using the generated `failure_summary.md`
and `summary.json`:

- **Minimal reproduction steps** are included (exact `make e2e` command + relevant env vars and stage name).
- The workflow computes a **dedupe key** from:
  - failing stage name
  - exit code / error class (when available)
  - a stable hash of the first N lines of the failing stage's stderr (post-redaction)
- Before creating a new issue, the workflow searches existing open issues for the same dedupe key.
  - If found: it adds a comment with the new run link and artifact name.
  - If not found: it opens a new issue titled like `E2E failure: <stage> (<dedupe_key>)` and attaches the summary.

### Permissions/requirements
- The workflow uses `GITHUB_TOKEN` with `issues: write` permission.
- Issue bodies reference the Actions run URL and the uploaded artifact name for quick access.

## Troubleshooting

- CI failed but artifacts are missing: ensure the workflow uploads artifacts on failure (use `if: always()`).
- Local debugging: open `artifacts/e2e/<run_id>/failure_summary.md` and rerun the failing stage with the
  same environment variables shown there.
