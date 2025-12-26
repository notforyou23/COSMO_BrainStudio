# Project Roadmap (Outputs Pipeline)

This roadmap defines the planned evolution of the deterministic `/outputs/` artifact pipeline across iterative cycles. It is a living artifact updated only by the pipeline and intended to keep milestones, deliverables, and CI/CD expectations explicit.
## Principles

- **Deterministic generation**: Given the same inputs, the pipeline produces byte-stable artifacts (normalized newlines, stable ordering).
- **Artifact-first workflow**: Canonical project state is captured under `/outputs/` (docs and structured matrices) before code is expanded.
- **Small-cycle cadence**: Each cycle adds value while keeping diffs reviewable; changes should remain scoped and testable.
- **No placeholders**: Roadmap and companion artifacts must be complete statements (no TODO markers).
## Milestones (high level)

1. **M0: Stable structure (Stage 1)** — establish artifact rules and seed required artifacts.
2. **M1: Deterministic generator** — add a script that regenerates all `/outputs/` docs deterministically.
3. **M2: CI enforcement** — add CI checks to verify determinism, formatting, and coverage completeness.
4. **M3: Expansion & maintenance** — enrich matrices, add additional artifacts, and codify update cadence with changelog notes.
## Cycles & Deliverables

### Cycle 1 (current): Stage 1 — Seed roadmap
**Goal**: Create a roadmap artifact that guides subsequent runs.
**Primary deliverable**: `outputs/roadmap.md`
**Acceptance**:
- Captures milestones, cycle plan, and evolution rules for future pipeline runs.
- Uses stable markdown conventions (headings, bullet lists, consistent terminology).
- No external references required to interpret the document.

### Cycle 2: Establish `/outputs/` conventions and required companion artifacts
**Goal**: Ensure every future cycle has a stable structure to build on.
**Deliverables**:
- `outputs/README.md` (artifact rules, naming, determinism, update cadence)
- `outputs/bibliography.md` (curated sources and citation notes)
- `outputs/coverage_matrix.md` (requirements → files/tests/CI mapping)
**Acceptance**:
- Each file is complete and self-describing.
- Stable ordering and sections; no placeholders.

### Cycle 3: Add deterministic generator script
**Goal**: Make artifact updates reproducible and reviewable.
**Deliverables**:
- `scripts/generate_outputs.py` that regenerates all required artifacts.
- Optional `scripts/run_pipeline.py` wrapper to run stages in order.
**Acceptance**:
- Idempotent: running twice produces no diffs.
- Writes only under `/outputs/` unless explicitly configured.

### Cycle 4: CI/CD checks and gates
**Goal**: Prevent drift and ensure artifacts remain authoritative.
**Deliverables**:
- CI job to run generator and fail on git diff.
- Markdown lint/format check (consistent headings, trailing newline).
- Coverage matrix gate: fails if required rows/columns are missing.
**Acceptance**:
- CI is fast and deterministic; failures are actionable.

### Cycle 5+: Expand coverage and governance
**Goal**: Increase completeness and clarity over time.
**Potential deliverables** (added only when needed):
- `outputs/evaluation_cadence.md` (review rhythm, release checklist)
- `outputs/changelog.md` (artifact changes by cycle)
- `outputs/risks_and_assumptions.md` (tracked risks, mitigations)
**Acceptance**:
- Every new artifact has a clear purpose and an owner process (who updates via pipeline).
## Evolution Plan (how this roadmap changes)

- This file changes only when a cycle is completed or when scope is re-baselined.
- New cycles should be appended, and completed cycles should be marked with outcomes (kept concise).
- If acceptance criteria change, document the rationale in the affected cycle section.
- Keep the roadmap under ~200 lines by summarizing historical cycles into milestones as the project matures.
## CI/CD Expectations (target state)

When CI is present, the following checks should exist and remain green:
- **Generate-and-diff**: run generator; fail if `/outputs/` differs.
- **Schema/structure checks**: verify required files exist and have required headings.
- **Coverage checks**: ensure coverage matrix includes all tracked requirements and references to tests/CI steps.
- **Formatting**: enforce trailing newline and stable markdown style.
## Definition of Done (for a cycle)

A cycle is considered complete when:
- Deliverables listed for the cycle exist and are coherent.
- Changes are deterministic and reproducible.
- Coverage matrix is updated to reflect the new/changed deliverables.
- CI expectations (if implemented) are updated accordingly.
