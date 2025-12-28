# /outputs Deliverables Index

This directory is the single, stable handoff location for all generated artifacts (simulation, test evidence, compliance/traceability, operational runbooks, and model packages). It is organized into predictable subfolders so downstream consumers can locate deliverables without knowing internal build details.

## Directory layout (expected)

- `outputs/models/` — packaged models, weights, configs, exported formats, and model cards.
- `outputs/compliance/` — requirements mapping, traceability, standards evidence, and audit-ready artifacts.
- `outputs/ops/` — operational docs: runbooks, deployment notes, monitoring/alerts, incident playbooks.
- `outputs/sim/` — simulation inputs/outputs, plots, logs, and aggregated results packs.
- `outputs/tests/` — test plans, matrices, procedures, logs, and summarized evidence.

If a folder is missing, it is still part of the intended contract; create it when the first artifact of that type is produced.

## Deliverables index

### Goal 1 — Simulation results pack (placeholder spec)
Location (contract): `outputs/sim/goal_1_simulation_results_pack.md` plus supporting files under `outputs/sim/`.

Acceptance criteria:
1. **Reproducibility:** Includes a run manifest capturing scenario IDs, seed(s), version/commit identifier (or build tag), and execution environment notes.
2. **Inputs captured:** Simulation configuration files and any parameter sweeps are saved alongside the pack or linked with exact paths.
3. **Outputs captured:** Raw outputs (logs/telemetry) and derived summaries (tables/plots) are provided; all summary figures are traceable to raw sources.
4. **Coverage statement:** Lists scenarios executed and clearly marks any planned scenarios not run, with reason codes.
5. **Quality checks:** States pass/fail criteria used for simulation acceptance and reports results per scenario.
6. **Packaging:** Provides a single top-level entry document (the pack) with links to all referenced artifacts, using relative paths under `outputs/sim/`.

### Goal 2 — Test matrix + design rules (placeholder spec)
Location (contract): `outputs/tests/goal_2_test_matrix.md` and `outputs/tests/goal_2_design_rules.md` plus supporting evidence under `outputs/tests/`.

Acceptance criteria (test matrix):
1. **Traceability:** Each test case maps to a requirement or objective identifier and notes the verification method (analysis/sim/test/inspection).
2. **Clear definition:** Every test includes purpose, preconditions, procedure, expected results, and measurable pass/fail thresholds.
3. **Coverage:** Matrix summarizes coverage across requirements and risk areas; gaps are explicitly listed with rationale and planned mitigation.
4. **Evidence hooks:** Defines where logs/results will be stored under `outputs/tests/` and how to interpret them.
5. **Versioning:** Matrix records revision history and the version/build it applies to.

Acceptance criteria (design rules):
1. **Actionable rules:** Rules are written as testable “shall/should” statements with rationale and scope.
2. **Constraints captured:** Includes interfaces, limits, safety/quality constraints, and any non-functional requirements that impact design.
3. **Verification link:** Each rule references how it will be verified (test/matrix row, simulation check, inspection).
4. **Change control:** Includes revision history and ownership/approver fields.

## How to use this index

- Producers: place artifacts in the appropriate subfolder and update/attach the corresponding goal placeholder documents when ready.
- Consumers: start from this README, then navigate to `outputs/sim/` for simulation artifacts and `outputs/tests/` for verification artifacts; compliance and ops materials are in their dedicated folders.

## Conventions

- Prefer relative links within `/outputs` so the bundle is portable.
- Name files consistently with a leading goal tag when applicable (e.g., `goal_1_*`, `goal_2_*`).
- Store large raw data under the relevant folder and keep summary documents lightweight with links.
