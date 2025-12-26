# Scaffold QA Harness (README_QA)

This document explains how to run the single-command validation harness that:
1) runs the scaffold generator deterministically, then
2) validates required artifacts under `outputs/`, and
3) writes a pass/fail report under `outputs/qa/`.

## Quick start (single command)

From the repository/project root, run:

- `python scripts/validate_scaffold.py`

Common options (if implemented in your harness):
- `python scripts/validate_scaffold.py --help`
- `python scripts/validate_scaffold.py --strict` (treat warnings as failures)
- `python scripts/validate_scaffold.py --json` (ensure JSON report is written)
- `python scripts/validate_scaffold.py --clean` (clear prior outputs before running)

If your environment prefers modules:
- `python -m scripts.validate_scaffold` (only if `scripts` is importable)

## What the harness does

1) Locates the project root and the deterministic `outputs/` directory.
2) Invokes the scaffold generator in a deterministic way (stable paths, stable filenames).
3) Verifies required artifacts exist in `outputs/`.
4) Produces:
   - a human-readable report (Markdown or text) and
   - a machine-readable JSON summary,
   saved under `outputs/qa/`.
5) Exits with a non-zero code if validation fails.

## Required artifacts checked in outputs/

The harness should verify that the following files exist under `outputs/`:

Core scaffold outputs:
- `outputs/REPORT_OUTLINE.md`
- `outputs/CASE_STUDY_TEMPLATE.md`
- `outputs/METADATA_SCHEMA.md`
- `outputs/CASE_STUDIES_INDEX.csv`

Rights artifacts (names may vary by project, but must exist as a set):
- A top-level rights or licensing notice (examples):
  - `outputs/RIGHTS.md`
  - `outputs/LICENSE.txt` or `outputs/LICENSE.md`
  - `outputs/NOTICE.txt` or `outputs/NOTICE.md`
- If the project defines a specific rights bundle, the harness should check that bundle explicitly
  (e.g., `outputs/rights/` directory with the expected files inside).

Notes:
- If your project uses a dedicated rights directory (e.g., `outputs/rights/`), the harness should
  validate both the directory exists and the required files inside it exist.
- If multiple acceptable filenames are supported (e.g., `LICENSE.md` vs `LICENSE.txt`), the harness
  should pass when any acceptable alternative is present.

## Where reports are written

After a run, look in:

- `outputs/qa/`

Typical outputs:
- `outputs/qa/validation_report.md` (human-readable)
- `outputs/qa/validation_report.json` (machine-readable)

The exact filenames may differ, but the harness should always write at least one human-readable
report and one JSON report for CI consumption.

## How to interpret the reports

Human-readable report (Markdown/text) should include:
- Timestamp
- Generator invocation details (command/module used)
- List of checks performed
- PASS/FAIL per check
- Summary counts (passed/failed/warned)
- If failures occur: actionable messages (missing file paths, unacceptable alternatives, etc.)

JSON report should include fields similar to:
- `status`: `"PASS"` or `"FAIL"`
- `checks`: list of objects with:
  - `name`
  - `status` (`PASS`/`FAIL`/`WARN`)
  - `details` (e.g., missing paths)
- `artifacts`: detected paths (optional but useful)
- `started_at`, `finished_at`, `duration_seconds` (recommended)

## Exit codes (recommended)

For CI and scripting, the harness should use conventional exit codes:
- `0`: all required checks passed
- `1`: one or more required checks failed
- `2`: unexpected execution error (exception, generator invocation failure, etc.)

## CI usage example

A minimal CI step can be:

- `python scripts/validate_scaffold.py`

Then archive:
- `outputs/qa/validation_report.*`
- optionally `outputs/*` artifacts for debugging

## Troubleshooting

- Missing outputs:
  - Ensure the scaffold generator actually writes into `outputs/` (deterministic location).
  - Run the harness with verbose logging if available.
- Rights artifacts failing:
  - Confirm which rights files are considered valid in your project and align the harness rules.
- Stale artifacts:
  - Use `--clean` if supported, or remove `outputs/` before running to validate a fresh scaffold.

## Determinism guidance (recommended)

To ensure reliable validation:
- Always write to the same `outputs/` path.
- Use stable filenames (no timestamps in required artifact names).
- If content hashes or metadata are produced, store them in `outputs/qa/` rather than renaming
  required top-level artifacts.
