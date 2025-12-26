# Evaluation & Shipping Loop (Per-Cycle)

This document defines the repeatable evaluation loop used to ship artifacts across cycles, with explicit shipping rules and acceptance criteria per cycle. It is written to be used both by humans and automation.

## Shared Definitions

- **Artifact**: Any file tracked in the project (e.g., `coverage_matrix.csv`, `eval_loop.md`, `index.md`, `manifest.json`).
- **Cycle**: A bounded iteration (C0, C1, C2, C3...) with a defined shipping target and acceptance tests.
- **Status** (recommended): `planned | in_progress | draft | review | shipped | blocked | deprecated`.
- **Stable ontology columns** (for `coverage_matrix.csv`): `domain, subtopic, artifact_types, status, cycle_target, links`.

## Universal Shipping Rules (All Cycles)

1. **No placeholders**: No “TODO”, “TBD”, or empty sections that are required for the cycle’s scope.
2. **Reproducible writes**: Generated/updated files must be deterministically produced given the same inputs.
3. **Link integrity**: All links in `outputs/index.md` and `outputs/manifest.json` must resolve to existing paths.
4. **Atomicity**: A cycle ships only when all acceptance criteria for that cycle pass.
5. **Traceability**: Each shipped artifact must be represented in `outputs/manifest.json` with at least: `path`, `category`, and `purpose` (or equivalent metadata).
6. **Coverage update**: Every shipped change must be reflected in `outputs/coverage_matrix.csv` (status and/or links and/or cycle_target).

## Universal Evaluation Loop (Run Each Cycle)

1. **Plan**: Select scope (rows/domains/subtopics) and set `cycle_target`.
2. **Build**: Create/update artifacts.
3. **Self-check**: Run formatting and basic validation (CSV columns present; JSON parseable; Markdown readable).
4. **Review**: Ensure acceptance criteria for the active cycle are met.
5. **Ship**: Update `status=shipped`, update `links`, refresh `index.md`, refresh `manifest.json`.
6. **Post-ship**: Record deltas and known limitations (as explicit notes inside the relevant artifact, not as TODOs).

## Cycle Targets, Shipping Rules, and Acceptance Criteria

### C0 — Bootstrap (Scaffolding)
**Goal**: Establish minimal infrastructure so subsequent cycles can reliably iterate.

**Shipping rules (C0)**:
- Create the baseline tracking and navigation artifacts.
- Keep ontology stable and explicit.
- Prefer minimal but complete content over broad scope.

**Acceptance criteria (C0)**:
- `outputs/coverage_matrix.csv` exists and includes the exact stable ontology columns:
  - `domain, subtopic, artifact_types, status, cycle_target, links`
- `outputs/coverage_matrix.csv` includes an initial row set covering the project’s core domains/subtopics.
- `outputs/eval_loop.md` exists and defines per-cycle rules/criteria (this file).
- `outputs/index.md` links to `coverage_matrix.csv` and `eval_loop.md`.
- `outputs/manifest.json` includes entries for `coverage_matrix.csv` and `eval_loop.md` with correct paths and categories.
- All referenced files exist on disk and are readable.

### C1 — MVP Content (First Useful Pass)
**Goal**: Produce a first useful set of artifacts that can be consumed by users/automation.

**Shipping rules (C1)**:
- Expand rows in `coverage_matrix.csv` to cover the intended initial scope.
- For each row targeted in C1, ensure at least one concrete artifact link exists.
- Avoid broad refactors; focus on completing the MVP set.

**Acceptance criteria (C1)**:
- For all rows with `cycle_target=C1`, `status` is not `planned` (must be `draft|review|shipped|blocked`).
- For all `cycle_target=C1` rows that are not `blocked`, `links` contains at least one valid, existing path.
- `outputs/index.md` includes a brief “What’s inside” section and links remain valid.
- `outputs/manifest.json` is valid JSON and lists all shipped C1 artifacts (at minimum by path).

### C2 — Hardening (Quality, Consistency, Automation)
**Goal**: Raise confidence via consistency checks and tighter definitions.

**Shipping rules (C2)**:
- Enforce consistency of terminology (domain/subtopic naming) and link formats.
- Ensure manifest metadata is complete enough for downstream automation.
- Add lightweight validation steps (scripted or documented) and ensure they pass.

**Acceptance criteria (C2)**:
- No duplicate `domain/subtopic/artifact_types` combinations in `coverage_matrix.csv` unless explicitly justified (e.g., versioned artifacts).
- `links` values use a consistent format (recommended: relative `outputs/...` paths separated by `;`).
- `outputs/manifest.json` includes for each artifact: `path`, `category`, `purpose`, and optional `depends_on`/`generated_by` if applicable.
- All C2-targeted rows are `shipped` or explicitly `blocked` with a short reason recorded in the row’s `links` field (e.g., a note link).

### C3 — Expansion (Broader Coverage + Maintenance)
**Goal**: Extend coverage while keeping maintenance cost low.

**Shipping rules (C3)**:
- Any new domain/subtopic must include: definition, owner/intent (can be implicit via purpose), and at least one artifact type.
- Prefer extending the matrix and manifest rather than creating ad-hoc documents.
- Deprecations must be explicit and non-breaking (keep stubs/redirect notes rather than deleting without record).

**Acceptance criteria (C3)**:
- New rows added in C3 have complete ontology fields and at least one valid link.
- Deprecated artifacts remain listed in `manifest.json` with `status: deprecated` (or equivalent metadata) and a replacement pointer.
- `outputs/index.md` remains a coherent landing page (no dead links; includes the newest key artifacts).

## Handling “Blocked” Work (Any Cycle)

If something is blocked:
- Set `status=blocked`.
- Keep `cycle_target` unchanged (so it remains visible).
- Put a short, concrete blocker note in `links` (either a path to a note artifact or an inline reason if the schema allows).
- A blocked item can ship as “blocked” only if the cycle’s acceptance criteria explicitly allow it (as above).

## Completion Definition (Cycle Close)

A cycle is considered closed when:
- All acceptance criteria for that cycle pass.
- Index and manifest are updated to reflect what shipped.
- The coverage matrix accurately reflects current status and link destinations.
