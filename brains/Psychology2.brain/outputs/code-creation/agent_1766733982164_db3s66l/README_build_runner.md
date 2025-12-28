# One-command build runner (artifact gate → taxonomy validation → meta-analysis demo)

This project provides a single command that runs three build verification steps **in order** and **fails fast** on the first error:

1. **artifact gate** (checks required artifacts exist / are well-formed)
2. **taxonomy validation** (validates taxonomy/labels/consistency rules)
3. **meta-analysis demo** (runs a small end-to-end demo on the validated artifacts)

All outputs are normalized under: `runtime/_build/` (step logs, step summaries, and a final status summary).
## Quick start

Run from the repo root:

- As a module:
  - `python -m src.build_runner`
- As a script:
  - `python src/build_runner.py`

Typical CI usage (deterministic, fail-fast):
- `python -m src.build_runner --fail-fast --out runtime/_build`

If the runner exits non-zero, the failing step’s logs will be in `runtime/_build/<run_id>/<step_name>/` and the overall status will be recorded in `runtime/_build/<run_id>/final_summary.json`.
## Expected output layout under `runtime/_build/`

Each invocation creates a new run directory (often timestamp-based), containing per-step outputs plus a final summary:

runtime/_build/
  <run_id>/
    build_info.json
    artifact_gate/
      raw.log
      stdout.txt
      stderr.txt
      step_summary.json
      outputs/           (step-specific files, if any)
    taxonomy_validation/
      raw.log
      stdout.txt
      stderr.txt
      step_summary.json
      outputs/
    meta_analysis_demo/
      raw.log
      stdout.txt
      stderr.txt
      step_summary.json
      outputs/
    final_summary.json
    final_status.txt

Notes:
- `raw.log` is the combined human-readable log stream for the step.
- `stdout.txt` / `stderr.txt` capture the underlying tool output verbatim.
- `step_summary.json` is a structured record of the command, duration, return code, and key paths.
- `final_summary.json` aggregates outcomes across steps and is the canonical artifact for CI parsing.
## One-command examples

Run with defaults:
- `python -m src.build_runner`

Force a known output root and show where artifacts were written:
- `python -m src.build_runner --out runtime/_build --print-paths`

Stop immediately when a step fails (recommended for CI):
- `python -m src.build_runner --fail-fast`

Re-run a specific step set (if supported by CLI flags):
- `python -m src.build_runner --steps artifact_gate,taxonomy_validation`

Tip: When debugging, open the most recent `runtime/_build/<run_id>/final_summary.json` and then jump into the failing step directory to read `raw.log` and `stderr.txt`.
## Interpreting the final summary status

The runner always writes a final summary, even if a step fails early.

`final_status.txt` contains a single word:
- `PASS` (all requested steps completed successfully)
- `FAIL` (a step failed; runner exited non-zero)
- `ERROR` (unexpected runner error, e.g., exception before/while launching a step)

`final_summary.json` (example shape):

{
  "run_id": "20250101_120000",
  "out_root": "runtime/_build",
  "status": "FAIL",
  "fail_fast": true,
  "started_at": "2025-01-01T12:00:00Z",
  "finished_at": "2025-01-01T12:00:13Z",
  "steps": [
    {"name": "artifact_gate", "status": "PASS", "returncode": 0, "dir": "runtime/_build/<run_id>/artifact_gate"},
    {"name": "taxonomy_validation", "status": "FAIL", "returncode": 2, "dir": "runtime/_build/<run_id>/taxonomy_validation"},
    {"name": "meta_analysis_demo", "status": "SKIPPED", "returncode": null, "dir": "runtime/_build/<run_id>/meta_analysis_demo"}
  ],
  "failure": {
    "step": "taxonomy_validation",
    "message": "See runtime/_build/<run_id>/taxonomy_validation/stderr.txt"
  }
}

Conventions:
- `PASS`: step completed with return code 0.
- `FAIL`: step ran and returned non-zero.
- `SKIPPED`: step not run because an earlier step failed (fail-fast) or was not requested.
- `ERROR`: runner-level failure (e.g., could not start subprocess).
## What to do when the runner fails

1. Open: `runtime/_build/<run_id>/final_summary.json` and identify the failing step.
2. Read the failing step’s `raw.log` first for context.
3. If it’s a tool error, check `stderr.txt` and then `stdout.txt`.
4. If you need reproducibility, re-run the runner and keep `--out runtime/_build` (same layout every time, different `<run_id>`).

CI recommendation:
- Treat non-zero exit code as failure.
- Archive `runtime/_build/<run_id>/` as the build artifact for post-mortem analysis.
