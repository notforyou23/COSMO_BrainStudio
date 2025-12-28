from __future__ import annotations

from pathlib import Path


README = """# Outputs Deliverables Index

This `/outputs` directory is the single home for generated artifacts and project deliverables.

## Directory map
- `outputs/models/` — model artifacts (e.g., checkpoints, exported weights, model cards)
- `outputs/compliance/` — compliance, traceability, audit evidence, and sign-off artifacts
- `outputs/ops/` — operational docs/runbooks, deployment notes, monitoring artifacts
- `outputs/sim/` — simulation inputs/outputs and analysis, incl. Goal 1 pack
- `outputs/tests/` — test plans, matrices, results, and design rules, incl. Goal 2 pack

## Goal placeholders
- Goal 1 (simulation results pack): `outputs/sim/goal_1_simulation_results_pack.md`
- Goal 2 (test matrix + design rules): `outputs/tests/goal_2_test_matrix_and_design_rules.md`

## Conventions
- Prefer stable, human-readable filenames.
- Store figures/tables alongside the markdown that references them.
- If an artifact is generated, include enough metadata to reproduce it (script name, version/commit, parameters).
"""


GOAL1 = """# Goal 1 — Simulation Results Pack (Placeholder)

## Purpose
Collect and present the simulation evidence needed to assess performance and support downstream compliance/testing.

## Acceptance criteria (must all be satisfied)
1. **Reproducibility**: Document how to reproduce the simulation (script/command, parameters, random seeds, environment notes).
2. **Inputs**: List and/or link all simulation inputs (scenarios, configs, datasets) with versions/hashes when applicable.
3. **Outputs**: Provide links to primary outputs (raw logs/results files) stored under `outputs/sim/`.
4. **Summary metrics**: Include a concise table of key metrics (with units) and the aggregation method.
5. **Plots/tables**: Include at least one visualization or table supporting the summary metrics.
6. **Assumptions & limitations**: State modeling assumptions, constraints, and known limitations.
7. **Change log**: Record major changes to scenarios/configs and why.

## Contents checklist
- [ ] Run configuration and command line
- [ ] Scenario descriptions
- [ ] Raw results locations
- [ ] Metric definitions
- [ ] Summary tables/plots
- [ ] Notes on anomalies/outliers
"""


GOAL2 = """# Goal 2 — Test Matrix + Design Rules (Placeholder)

## Purpose
Define a traceable, executable test matrix and a compact set of design rules/constraints that implementations must follow.

## Acceptance criteria (must all be satisfied)
1. **Coverage**: Test matrix enumerates functional, non-functional, and edge-case tests with clear IDs.
2. **Traceability**: Each test maps to a requirement/design rule (bidirectional mapping preferred).
3. **Procedure**: Each test includes setup, steps, pass/fail criteria, and required artifacts (logs, screenshots, reports).
4. **Data & environments**: Specify required test data and target environments (versions, hardware assumptions).
5. **Automation readiness**: Identify which tests are automatable and provide hooks/commands where applicable.
6. **Design rules**: Provide a numbered list of explicit constraints (inputs/outputs contracts, safety limits, performance bounds).
7. **Reporting**: Define how results are recorded (file naming, location under `outputs/tests/`, summary format).

## Minimal matrix template
| Test ID | Name | Type | Requirement/Rule | Steps (summary) | Pass/Fail | Artifacts |
|---|---|---|---|---|---|---|
| T-001 |  |  |  |  |  |  |

## Design rules template
1. DR-001: ...
2. DR-002: ...
"""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def init_outputs_scaffold(root: Path | None = None) -> Path:
    base = root if root is not None else Path(__file__).resolve().parents[1]
    out = base / "outputs"
    subdirs = ["models", "compliance", "ops", "sim", "tests"]
    out.mkdir(parents=True, exist_ok=True)
    _write(out / ".gitkeep", "")
    for sd in subdirs:
        d = out / sd
        d.mkdir(parents=True, exist_ok=True)
        _write(d / ".gitkeep", "")
    _write(out / "README.md", README)
    _write(out / "sim" / "goal_1_simulation_results_pack.md", GOAL1)
    _write(out / "tests" / "goal_2_test_matrix_and_design_rules.md", GOAL2)
    return out


def main() -> None:
    out = init_outputs_scaffold()
    print(f"INIT_OUTPUTS_SCAFFOLD_OK:{out}")


if __name__ == "__main__":
    main()
