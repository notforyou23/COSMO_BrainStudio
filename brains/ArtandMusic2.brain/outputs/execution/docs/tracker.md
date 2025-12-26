# QA Tracker (Canonical)

This tracker defines the single supported way to generate QA evidence and validation for this project.

## Canonical QA command (only supported entry point)

Run QA from the project root:

python scripts/qa_run.py

Notes:
- This is the only supported QA command; do not run individual QA scripts directly for tracked evidence.
- The runner is responsible for producing the standardized artifact tree and invoking scripts/validate_outputs.py against the produced artifacts.

## Canonical artifact location (only supported evidence/validation location)

All QA evidence MUST be written under:

outputs/qa/<run_id>/

Anything written outside outputs/qa/ during QA runs is considered non-canonical and is not valid as QA evidence.

## Required artifact structure (produced by the canonical command)

outputs/qa/<run_id>/
  index.json
  manifest.json
  logs/
  reports/
  artifacts/

Definitions:
- <run_id>: unique run identifier created by the runner.
- index.json: top-level pointer file (run metadata + canonical paths).
- manifest.json: enumerated list of produced files with hashes/metadata for reproducibility.
- logs/: stdout/stderr + execution logs.
- reports/: human-readable summaries (e.g., markdown, html, junit xml if applicable).
- artifacts/: any additional QA evidence outputs (images, csv, json, etc.).

## How to reference QA results in issues/PRs

When attaching QA evidence, reference only:
- outputs/qa/<run_id>/index.json (preferred), or
- outputs/qa/<run_id>/ (the run root)

Do not reference ad-hoc paths (e.g., outputs/tmp, outputs/results, local scratch files).

## Acceptance criteria (for a QA run to be “tracked”)

A run is considered tracked only if:
1) It was executed via: python scripts/qa_run.py
2) All produced files are under outputs/qa/<run_id>/
3) validate_outputs.py was executed on the produced outputs/qa/<run_id>/ tree
4) index.json and manifest.json exist and describe the run

## Quick checklist

- [ ] Run: python scripts/qa_run.py
- [ ] Confirm artifacts exist only under outputs/qa/<run_id>/
- [ ] Use outputs/qa/<run_id>/index.json as the single linkable entry point
