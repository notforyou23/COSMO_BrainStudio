# QA Gate (single-command runner)

This project ships a QA “gate” that validates `DRAFT_REPORT_v0.md` plus the pilot artifacts, and emits two machine-/human-friendly outputs:
- `QA_REPORT.json` (authoritative, machine-readable)
- `QA_REPORT.md` (human-readable summary)

The QA gate is intended to be the single entrypoint for CI and local runs: one command in, two reports out, and a non-zero exit code on failure.
## One command to run QA

From the repo root:

- `bash scripts/qa_run.sh`

This command runs the full QA suite against:
- the draft report: `DRAFT_REPORT_v0.md`
- the pilot artifacts (as defined by the project’s QA checks)

On success, it writes:
- `QA_REPORT.json`
- `QA_REPORT.md`

If any required check fails, the command exits non-zero (useful for CI gating).
## What is validated

The QA gate orchestrates a set of checks implemented in `qa/qa_checks.py`. Checks are designed to be:
- deterministic (same inputs => same results)
- actionable (each failing check includes a remediation pointer)
- reportable (per-check status, message, and metadata)

Typical validation categories include:
- Presence and readability of required inputs (e.g., report file, artifact files)
- Structural expectations for the draft report (e.g., minimal sections/headers, links)
- Pilot artifact integrity (e.g., expected paths, file types, required fields)
- Report schema conformance and consistency across outputs

The canonical structure of `QA_REPORT.json` is defined by:
- `qa/schema_qa_report.json`

Remediation pointers referenced by checks are sourced from:
- `qa/remediation_catalog.json`
## Outputs

### QA_REPORT.json (machine-readable)

`QA_REPORT.json` is the source of truth for status. It contains:
- Run metadata (e.g., tool version, timestamp, inputs)
- A list of per-check results
- An overall outcome derived from the per-check statuses

Per-check results include:
- `check_id`: stable identifier for the check (used for remediation mapping)
- `status`: one of `PASS`, `FAIL`, or `WARN`
- `message`: short diagnostic summary
- `details`: optional structured details to aid debugging
- `remediation`: a pointer (or pointers) explaining how to fix failures

Consumers (CI, scripts, dashboards) should rely on `QA_REPORT.json` for programmatic decisions.
### QA_REPORT.md (human-readable)

`QA_REPORT.md` mirrors the JSON results in a readable format:
- Overall summary (pass/fail/warn counts)
- Per-check table/sections showing status and messages
- Remediation pointers for any `FAIL` / `WARN` items

Use this report for quick review in PRs, release checklists, and manual QA signoff.
## Interpreting statuses

- `PASS`: check met requirements; no action needed.
- `WARN`: check detected a non-blocking issue; recommended to remediate, but the gate may still pass depending on policy.
- `FAIL`: check detected a blocking issue; the QA command exits non-zero.

The exit code is intended to reflect whether the overall gate passed (all required checks passed) or failed (any blocking check failed).
## Remediation pointers

Every check is expected to provide a remediation pointer when it does not `PASS`.
Remediation pointers are intentionally stable and reusable across both reports:
- In JSON: included under the per-check `remediation` field
- In Markdown: shown next to the failing/warning check

Remediation pointers map to entries in `qa/remediation_catalog.json` (e.g., a short fix recipe, file/section to update, or a link to project guidance).
## Troubleshooting

If the command fails:
1. Open `QA_REPORT.md` to see which checks failed and the recommended remediation.
2. For deeper debugging, inspect `QA_REPORT.json` and look at each failing check’s `details` field.
3. Re-run the command after applying the remediation steps until all required checks pass.

If you need to integrate the gate into automation, prefer parsing `QA_REPORT.json` and enforcing policy based on `status` and `check_id`.
