# Outputs Directory

This directory holds **cycle artifacts** (documents, data extracts, figures, reports) that must exist on disk at the end of a run. It is treated as the contract between the agent workflow and downstream users/CI: if required artifacts are missing or empty, the cycle is not considered complete.

## Principles

- **Deterministic location:** artifacts live under `outputs/` so they are easy to collect, review, and version.
- **Non-empty artifacts:** required files must exist and contain content (size > 0 bytes).
- **Versioned log:** each cycle adds an entry to a versioned changelog so changes are traceable.
- **Separation of concerns:** source code belongs in `src/` and `scripts/`; only deliverables go in `outputs/`.

## Required folder structure

The minimal expected structure is:

- `outputs/`
  - `README.md` (this file)
  - `CHANGELOG.md` (versioned, append-only; see below)
  - `artifacts/` (primary deliverables for the cycle)
  - `artifacts/raw/` (unmodified exports, snapshots, or inputs captured for reproducibility)
  - `artifacts/processed/` (cleaned/derived files used for analysis)
  - `artifacts/reports/` (human-readable reports: markdown, pdf, html)
  - `artifacts/figures/` (plots, images)
  - `tmp/` (optional; non-critical scratch outputs; may be cleared)

Notes:
- Additional subfolders are allowed, but the ones above are the baseline for consistency.
- If a cycle produces no deliverables of a given type, the folder may exist empty; **required files** must still be non-empty.

## CHANGELOG.md expectations (versioned)

`outputs/CHANGELOG.md` must:
- Start with a top heading and follow a simple, readable format (e.g., Keep a Changelog-style sections).
- Include a **new entry per cycle/run** with:
  - date (YYYY-MM-DD)
  - a version tag (e.g., `v0.1.0`, `v0.1.1`, or `cycle-0009`)
  - a short list of added/changed/fixed items
- Be append-only (do not rewrite history except to correct factual errors).

Recommended entry template:

- `## [vX.Y.Z] - YYYY-MM-DD`
  - `### Added` / `### Changed` / `### Fixed`
  - Bullet list of artifacts created or updated (include relative paths).

## Artifact completion gate (success criteria)

A cycle is considered successful only if:

1. **Structure exists**
   - `outputs/` exists
   - `outputs/README.md` exists
   - `outputs/CHANGELOG.md` exists
   - `outputs/artifacts/` exists (and key subfolders if used)

2. **Required files are non-empty**
   - `outputs/README.md` size > 0
   - `outputs/CHANGELOG.md` size > 0
   - Any run-declared “required artifacts” (e.g., final report) exist and size > 0

3. **Changelog updated**
   - A new version/cycle entry was appended for the current run.

## Automated check and manual checklist

Automation is expected via the artifact gate module/CLI:
- `src/artifact_gate.py` creates the folder structure (if missing), ensures README + CHANGELOG exist, and verifies required files are non-empty.
- `scripts/run_artifact_gate.py` runs the gate and exits non-zero on failure for CI/manual runs.

Manual checklist (use only if automation is unavailable):
- [ ] `outputs/README.md` exists and is non-empty
- [ ] `outputs/CHANGELOG.md` exists and includes an entry for this run
- [ ] All required deliverables listed for the run exist under `outputs/artifacts/` and are non-empty
- [ ] Paths in the changelog match what is present on disk
