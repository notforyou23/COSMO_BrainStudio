# Coverage Matrix

Purpose: track end-to-end completeness by mapping project requirements to concrete evidence (files), automated validation (tests/lints), and CI checks.

Legend: **Status** ∈ {Implemented, Partial, Planned}. “Partial” means some evidence exists but automation or CI enforcement is missing.
## Matrix

| ID | Requirement | Evidence (files/artifacts) | Validation (tests/lints) | CI enforcement | Status |
|---:|---|---|---|---|---|
| R1 | All generated artifacts live under `/outputs/` with documented conventions | `outputs/README.md` | Markdown lint (e.g., `markdownlint`) | CI job: `lint_markdown` | Planned |
| R2 | Deterministic generation: re-running the generator yields byte-identical artifacts unless inputs change | `scripts/generate_outputs.py`; `outputs/README.md` (determinism guarantees) | Unit test: run generator twice, compare hashes | CI job: `determinism_check` | Planned |
| R3 | A roadmap artifact exists describing cycles/milestones and evolution plan | `outputs/roadmap.md` | Markdown lint | CI job: `lint_markdown` | Planned |
| R4 | A bibliography artifact exists capturing sources and citation notes | `outputs/bibliography.md` | Markdown lint + link-check | CI job: `lint_markdown`, `link_check` | Planned |
| R5 | A structured coverage matrix exists and is kept current across cycles | `outputs/coverage_matrix.md` | Markdown lint | CI job: `lint_markdown` | Implemented |
| R6 | Generator script is safe, minimal, and only writes within `/outputs/` | `scripts/generate_outputs.py` | Unit test: filesystem write audit (no paths outside `/outputs/`) | CI job: `unit_tests` | Planned |
| R7 | Generator creates/updates the three baseline artifacts in a stable structure | `scripts/generate_outputs.py`; `outputs/README.md`; `outputs/roadmap.md`; `outputs/bibliography.md`; `outputs/coverage_matrix.md` | Unit test: expected files exist and contain required headings | CI job: `unit_tests` | Planned |
| R8 | Artifacts follow consistent metadata conventions (title, purpose, update cadence) | `outputs/README.md` + each artifact header | Markdown lint + custom check (required header fields) | CI job: `artifact_schema_check` | Planned |
| R9 | CI/CD is documented: required checks and their triggers are explicit | `outputs/README.md` (CI section) | Documentation check (presence of CI section + named jobs) | CI job: `artifact_schema_check` | Planned |
| R10 | Repository supports incremental evolution: changes are tracked by cycle with minimal churn | `outputs/roadmap.md` (cycle log) | Diff-based check (limits on reflow/format churn) | CI job: `churn_guard` | Planned |
## Update protocol

1. When a requirement is satisfied, mark **Status** as Implemented and ensure **Evidence** and **Validation/CI** are concrete (file paths and job/test names).
2. When adding new requirements, assign the next sequential `R#` and keep the table sorted by ID.
3. This file must remain deterministic and stable in formatting (pipe table, fixed column order) to support automated diffing.
