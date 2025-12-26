# QA Harness (CI/Regression Safeguard)

This document describes how to run the deterministic QA harness locally and in CI, how to interpret `QA_REPORT.json`, and how to troubleshoot failures—especially "write-policy" violations (outputs written outside the canonical `/outputs` tree).

## What this harness guarantees

1. A single, deterministic entrypoint runs the canonical QA command.
2. A required `/outputs` scaffold is created/normalized before QA starts.
3. The harness produces `outputs/QA_REPORT.json` on every run (uploaded as a CI artifact).
4. CI fails if:
   - the QA gate fails (non-zero exit / failed checks), or
   - any new/modified files are written outside the canonical `/outputs` tree (with allowlist support).

## Canonical paths & policies

- Canonical outputs root: `./outputs`
- Required report artifact: `./outputs/QA_REPORT.json`
- Write policy: during QA execution, the repository must not gain new/modified files outside `./outputs` (except allowlisted paths). This prevents flaky regressions and ensures all generated artifacts are captured and reviewable.

## Running locally

### Prerequisites
- Python 3.x
- Your project's normal QA dependencies installed (whatever the canonical QA command requires)

### Run the harness
From the repo root:
- `python scripts/ci_qa_harness.py`

Common options (names may vary by implementation):
- `--qa-cmd "<command>"` to override the canonical QA command if needed.
- `--allowlist path1,path2` to permit expected non-outputs writes (rare).
- `--outputs-dir outputs` to set the canonical outputs directory (should remain `outputs`).

### Expected results
- `outputs/QA_REPORT.json` is created/overwritten.
- Additional QA artifacts (logs, snapshots, junit, etc.) should also live under `outputs/`.

## Running in CI (GitHub Actions)

The workflow file `.github/workflows/qa-regression.yml` is expected to:
- Trigger on pushes and pull requests (and optionally a schedule).
- Run `python scripts/ci_qa_harness.py`.
- Upload `outputs/QA_REPORT.json` (and typically the whole `outputs/` tree) as an artifact.
- Fail the job if the harness exits non-zero.

To inspect results:
- Open the workflow run → Artifacts → download `outputs` artifact → view `outputs/QA_REPORT.json`.

## Interpreting outputs/QA_REPORT.json

`QA_REPORT.json` is the single source of truth for the run outcome. Typical fields you may see:

- `status`: overall status, e.g. `pass` / `fail`.
- `qa_command`: the command executed (string or argv list).
- `start_time` / `end_time` / `duration_seconds`: timing metadata.
- `exit_code`: exit code from the canonical QA command.
- `checks`: list/object of checks executed (lint/unit/integration/etc.) with per-check status.
- `write_policy`: results of outputs-only enforcement, e.g.:
  - `violations`: list of files written/modified outside `outputs/`.
  - `allowlist`: paths/globs that were exempted.
- `notes`: extra context (versions, environment, git SHA, etc.).

Pass criteria:
- `status == "pass"`
- `exit_code == 0`
- `write_policy.violations` empty (or absent)

Fail criteria:
- any of the above indicates failure, or the harness itself exits non-zero.

## Troubleshooting

### 1) QA gate failure (tests/lint fail)
Symptoms:
- CI job fails
- `QA_REPORT.json` shows `status: fail` and/or non-zero `exit_code`
Actions:
- Download artifacts and inspect logs under `outputs/`.
- Re-run locally with the same command; ensure you are using the repo’s canonical QA command.

### 2) Write-policy failure (files written outside ./outputs)
Symptoms:
- CI fails even if tests pass
- `QA_REPORT.json` lists one or more `write_policy.violations`
Typical causes:
- Tests generating caches (e.g., `.pytest_cache/`, `.mypy_cache/`)
- Tools writing to `$HOME`-relative locations that map into the repo
- Snapshot tests writing into source directories
- Formatting tools modifying tracked files during QA

Recommended fixes (in order):
1. Reconfigure the tool to write under `./outputs` (preferred).
   - Example: set cache dir to `outputs/cache/...`
2. Update the tool invocation to use a temp dir inside `outputs/`.
3. If truly unavoidable, add a narrow allowlist entry (last resort).
   - Keep allowlists specific (single file/path), not broad globs.

### 3) “False positive” write-policy detection
If a file is flagged but you believe it should not be:
- Confirm it was actually created/modified during the run (timestamps, git status).
- Ensure the validator compares against a pre-run snapshot and respects `.gitignore` behavior as designed.
- Check for line-ending normalization or formatting steps that rewrite files.

## Notes for contributors

- Do not rely on implicit side effects outside `outputs/` (no generating files under the repo root, package dirs, or `.git/`).
- If your change adds new generated artifacts, route them to `outputs/` so CI can collect them consistently.
- Treat `outputs/QA_REPORT.json` as the canonical interface for downstream reporting and dashboards.
