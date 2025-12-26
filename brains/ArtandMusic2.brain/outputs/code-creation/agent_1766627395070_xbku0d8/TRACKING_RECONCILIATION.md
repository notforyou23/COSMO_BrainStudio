# TRACKING_RECONCILIATION

This report is generated from the machine-readable ledger at `outputs/PROJECT_TRACKER.json` and summarizes current goal status plus validation checks.
## Snapshot

- Generated at (UTC): `2025-12-25T00:54:31+00:00`
- Ledger: `/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution/outputs/PROJECT_TRACKER.json`
- Goals: **3** (valid: **0**, invalid: **3**, warnings: **2**)
## Validation results

| Check | Status | Details |
| --- | --- | --- |
| Ledger load | PASS | Loaded from `/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution/outputs/PROJECT_TRACKER.json` |
| Top-level type | PASS | JSON array of goals |
| Required fields present | PASS | Missing field instances: 0 |
| Unique goal_id | PASS | Unique IDs: 3/3 |
| Type checks | FAIL | Type issues: 3 |
| progress_pct bounds | PASS | Out-of-range: 0 |
| last_updated format | PASS | Non-ISO timestamps: 0 |
| Enum sanity (priority/qa_status) | WARN | Unrecognized enum values: 2 |
## Goals summary

| goal_id | description | priority | progress_pct | qa_status | last_updated | row_status | notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| G001 | Create machine-readable project tracker ledger at outputs/PROJECT_TRACKER.json with required fields. | 1 | 100 | pass | 2025-12-25T00:52:30Z | INVALID | `priority` must be a string |
| G002 | Add scripts/update_tracker.py CLI to load/update outputs/PROJECT_TRACKER.json and generate TRACKING_RECONCILIATION.md. | 2 | 0 | not_started | 2025-12-25T00:52:30Z | INVALID | `priority` must be a string; Unrecognized qa_status value `not_started` |
| G003 | Generate TRACKING_RECONCILIATION.md from the tracker ledger with validation results and a summary table of goals. | 3 | 0 | not_started | 2025-12-25T00:52:30Z | INVALID | `priority` must be a string; Unrecognized qa_status value `not_started` |
## Interpretation rules (for humans)

- **progress_pct** is expected in the inclusive range **0..100**.
- **qa_status** should be one of: PASS / FAIL / WARN / PENDING / N/A (unrecognized values are warnings).
- **last_updated** should be ISO-8601 (e.g., `2025-12-25T00:00:00Z`).
