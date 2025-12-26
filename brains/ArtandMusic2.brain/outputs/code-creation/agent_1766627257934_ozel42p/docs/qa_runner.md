# QA Runner (single entrypoint)

This project standardizes **one** QA runner command that all workflows (CI and local) should call.

Primary entrypoint:
- `python -m qa.run [flags]`

Shell wrapper (optional, preferred in CI for simplicity):
- `scripts/qa_run.sh [flags]` (invokes `python -m qa.run` and passes through arguments)

The runner is responsible for:
- Orchestrating QA tools (format/lint/typecheck/tests/etc.)
- Writing artifacts to stable, machine-consumable locations
- Returning **non-zero exit codes** on failure for CI gating
## Quick start

Run the default QA suite:
- `python -m qa.run`

Run a subset:
- `python -m qa.run --only lint,typecheck`
- `python -m qa.run --skip format`

Save artifacts to a known directory:
- `python -m qa.run --out-dir .qa_artifacts`

Fail fast on first failing step:
- `python -m qa.run --fail-fast`
## CLI flags

Notes:
- Flags are identical whether you call `python -m qa.run` or `scripts/qa_run.sh`.
- Lists use comma-separated names (no spaces): `lint,typecheck,tests`.

Common flags:
- `--only NAMES`:
  Run only the named steps (comma-separated).
- `--skip NAMES`:
  Skip the named steps (comma-separated).
- `--list`:
  Print available steps and exit.
- `--fail-fast`:
  Stop at the first failed step (default behavior may run all and summarize).
- `--jobs N`:
  Concurrency for steps that support it (when applicable).
- `--timeout SECONDS`:
  Per-step timeout (when applicable).
- `--out-dir PATH`:
  Root directory for all QA artifacts (see “Stable output locations”).
- `--run-id ID`:
  Optional identifier to namespace a run under the output directory.
- `--format {text,json}`:
  Console output format. `json` is intended for CI log parsers.
- `--verbose`:
  More console logging.
- `--version`:
  Print runner version and exit.

Environment variables (override flags where applicable):
- `QA_OUT_DIR`:
  Same as `--out-dir`.
- `QA_RUN_ID`:
  Same as `--run-id`.
- `QA_FORMAT`:
  Same as `--format`.
## Step names

The runner exposes a stable set of step names. The exact implementation may vary by repo, but the names remain consistent so workflows can depend on them.

Typical step names:
- `scaffold`: validate required repo structure / generated assets (if applicable)
- `format`: auto-format (may be no-op in check-only mode)
- `lint`: style and static linting
- `typecheck`: static typing
- `tests`: unit/integration tests

Discover the authoritative list for this repo:
- `python -m qa.run --list`
## Exit codes (CI-friendly)

The runner guarantees non-zero exit codes on failure.

- `0`: All requested steps succeeded.
- `1`: One or more steps failed (tool returned non-zero, assertion failed, etc.).
- `2`: Usage error (invalid flag, unknown step name, conflicting options).
- `3`: Runner/internal error (unexpected exception, missing dependency, IO error).
- `124`: Timeout (a step exceeded `--timeout` or global run limit if enforced).

Workflows should treat any non-zero code as failure and surface runner output + artifacts.
## Stable output locations (artifacts)

All artifacts live under a single root output directory.

Resolution (highest precedence first):
1. `--out-dir PATH`
2. `QA_OUT_DIR`
3. Default: `<repo_root>/.qa_artifacts`

Run namespacing:
- If `--run-id` (or `QA_RUN_ID`) is provided, artifacts are written to:
  `<out_dir>/<run_id>/...`
- Otherwise:
  `<out_dir>/latest/...` (and the runner may rotate or overwrite)

Standard layout under the run directory:
- `summary.json`:
  Machine-readable run summary (steps, statuses, durations, exit code).
- `summary.txt`:
  Human-readable summary (mirrors console text format).
- `logs/`:
  One log file per step (stdout/stderr captured), e.g. `logs/lint.log`.
- `reports/`:
  Tool-produced reports (JUnit XML, coverage, SARIF), when available.
- `meta.json`:
  Environment metadata (python version, platform, timestamps, git info if available).

Workflows should upload the entire run directory as a build artifact to enable debugging.
## Workflow integration guidance

Recommended usage in CI:
- Use `scripts/qa_run.sh --format json --out-dir .qa_artifacts --run-id "$CI_JOB_ID"` (or similar).
- Always archive `<out_dir>/<run_id>` (or `<out_dir>/latest`) as a build artifact.
- Gate merges on exit code `0`.

Recommended usage locally:
- `python -m qa.run --out-dir .qa_artifacts`
- For quick iteration: `python -m qa.run --only lint,typecheck --fail-fast`

Important:
- Do not call underlying tools directly from workflows; call the runner so flags, paths, and exit codes stay consistent.
