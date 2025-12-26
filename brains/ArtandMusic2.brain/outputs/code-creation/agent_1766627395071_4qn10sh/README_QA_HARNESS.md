# QA/CI Harness (Regression Safeguard)

This project ships a deterministic QA harness intended to run on every PR/push (and on a schedule) to:
- Run the canonical QA command via a single entrypoint
- Write `QA_REPORT.json` under the canonical `/outputs` tree
- Fail the run if the QA gate fails
- Fail the run if any file is written/modified outside the canonical `/outputs` tree (with allowlist support)

This document explains how to run it locally and in CI, how to interpret `QA_REPORT.json`, and how to troubleshoot write-policy failures.
## Quick start (local)

From the repository root (recommended):
- Run the harness (single entrypoint):
  - `python scripts/ci_qa_harness.py`

Common variations (if supported by your harness implementation):
- Select a QA command override:
  - `python scripts/ci_qa_harness.py --qa-cmd "make qa"`
  - `python scripts/ci_qa_harness.py --qa-cmd "python -m qa.run"`
- Keep outputs from prior runs (otherwise scaffold may normalize/overwrite placeholders):
  - `python scripts/ci_qa_harness.py --keep-outputs`

Expected result:
- The harness creates/normalizes the canonical `outputs/` directory structure (deterministic scaffold).
- The harness runs the canonical QA command.
- The harness writes `outputs/QA_REPORT.json`.
- The harness validates that no new/modified files were written outside `outputs/` (except allowlisted paths).
## What CI runs

CI should run the same entrypoint as local runs so behavior is consistent:
- `python scripts/ci_qa_harness.py`

The GitHub Actions workflow (typically `.github/workflows/qa-regression.yml`) should:
- Trigger on `push` and `pull_request`
- Trigger on a scheduled cadence (cron)
- Upload `outputs/QA_REPORT.json` (and optionally the entire `outputs/` folder) as an artifact
- Fail the job if:
  - The QA gate fails (non-zero exit or explicit gate failure), OR
  - The write-policy validator detects writes outside `outputs/`.
## Canonical outputs contract

The harness enforces an outputs contract:
- All run artifacts MUST be written under `outputs/` (repo-relative).
- `outputs/QA_REPORT.json` is the canonical machine-readable summary.
- Any file written/modified outside `outputs/` is treated as a regression unless allowlisted.

Rationale:
- Keeps the repository clean during CI runs
- Prevents accidental commits of generated files
- Makes QA behavior reproducible and artifact-friendly
## QA_REPORT.json: how to read it

`outputs/QA_REPORT.json` is intended to be stable and machine-consumable. Exact fields may evolve, but you should generally expect:
- A top-level overall status (pass/fail)
- One or more checks with:
  - `name`
  - `status` (pass/fail/error/skip)
  - `details` (human-readable message, command output pointers, timings)
- Metadata:
  - timestamp
  - git ref/sha (in CI)
  - the QA command executed
  - environment info (python version, platform, etc.)

Typical usage:
- Humans: open the JSON and search for failed checks and their `details`.
- Automation: parse the JSON and gate merges/deployments on overall status.

If your CI uploads artifacts, download `QA_REPORT.json` to inspect failures without rerunning locally.
## Write-policy enforcement (outputs-only)

The harness should validate the repository after QA execution and fail if anything new/modified appears outside `outputs/`.
This is usually implemented via `scripts/validate_outputs.py` and commonly works like:
1) Snapshot file state before QA run
2) Run QA
3) Snapshot again
4) Compute new/modified paths
5) If any changed paths are outside `outputs/` (and not allowlisted), fail

Allowlist support:
- Some projects allow specific files to change (e.g., lockfiles) during QA.
- Prefer minimizing allowlists; treat each allowlisted path as technical debt.

If you see a failure like “writes outside outputs”, review:
- Which files were changed
- Which step created them (formatter, test, doc build, cache, etc.)
- Whether the tool can be configured to write under `outputs/` or disabled in CI
## Troubleshooting

### 1) QA gate fails
- Re-run locally:
  - `python scripts/ci_qa_harness.py`
- Inspect:
  - Console output
  - `outputs/QA_REPORT.json` (look for failing check details)
- Common fixes:
  - Update expected snapshots/baselines (if your QA flow uses them)
  - Fix deterministic ordering (sorting, seeded RNG)
  - Pin tool versions for stable behavior in CI

### 2) “Wrote files outside outputs/”
- Identify the offending paths from the harness/validator output.
- Typical culprits:
  - Test frameworks writing caches (e.g., `.pytest_cache/`)
  - Linters/formatters rewriting files
  - Doc generators writing to `docs/` or build directories
  - Tooling writing to `$HOME` or user-level caches
- Fix patterns:
  - Configure tools to output under `outputs/` (preferred)
  - Disable caches in CI (e.g., set env vars or CLI flags)
  - Add explicit cleanup steps inside the harness (only when necessary)
  - As a last resort, add a narrow allowlist entry

### 3) Artifact missing in CI
- Ensure the harness writes `outputs/QA_REPORT.json` even on failure (best practice).
- Confirm the workflow uploads artifacts from `outputs/`.
- Make sure CI job permissions and paths match the repo layout.

### 4) Local vs CI mismatch
- Confirm both run the same entrypoint (`scripts/ci_qa_harness.py`).
- Ensure python/tool versions match (use a lockfile or toolchain pinning).
- Avoid relying on undeclared environment variables; make harness defaults explicit.
## Minimal contract for contributors

Before opening a PR:
- Run: `python scripts/ci_qa_harness.py`
- Confirm:
  - QA passes
  - `outputs/QA_REPORT.json` is generated
  - No files are written/modified outside `outputs/`

If you need a tool to write outside `outputs/`, treat it as a bug to fix rather than normal behavior.
