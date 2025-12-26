# Roadmap v1 — `/outputs/` artifacts for the Python-script implementation mission

## Scope (Stage 1 seed deliverable)
This roadmap defines the planned deterministic artifacts to be produced in `/outputs/`, the milestones to create them, and acceptance criteria so each cycle can “ship” auditable deliverables.

## Guiding principles
- **Deterministic**: artifacts are generated/updated in a reproducible way from the same inputs.
- **Auditable**: every artifact states purpose, inputs, and acceptance checks.
- **Atomic shipping**: each cycle writes a small number of complete artifacts (no placeholders).
- **Tight budgets**: prefer short, high-signal Markdown and minimal diffs.
## Milestones and planned `/outputs/` artifacts

### M0 — Repository hygiene and artifact contract (foundational)
**Artifacts**
- `outputs/README.md` — rules, naming conventions, and “ship every cycle” checklist.

**Acceptance criteria**
- Defines what qualifies as an artifact, how updates are versioned (e.g., `_v1`, `_v2`), and what metadata each artifact must contain (purpose, date, inputs, checks).
- Includes an explicit checklist that can be executed each iteration (e.g., validate paths, confirm budgets, confirm no placeholders).
- Mentions that only files under `/outputs/` are written by the pipeline unless explicitly authorized.
### M1 — Seed deliverables (this iteration)
**Artifacts**
- `outputs/roadmap_v1.md` — this document.
- (Optionally) one additional “seed” artifact such as `outputs/bibliography_system_v1.md` *or* `outputs/data_model_v1.md`.

**Acceptance criteria**
- Roadmap lists all near-term artifacts with clear purpose and acceptance criteria.
- No `TODO`, `TBD`, or placeholder sections.
- Fits within the stage line budget and is readable as a standalone plan.
### M2 — Pipeline skeleton + run log format
**Artifacts**
- `outputs/pipeline_plan_v1.md` — stages, inputs, outputs, and invariants.
- `outputs/run_log_v1.jsonl` — append-only run records (one JSON object per run).

**Acceptance criteria**
- Pipeline plan defines: entrypoint, allowed write paths, deterministic ordering, and failure behavior.
- Run log schema includes: timestamp, stage, written files, hashes, and validation results.
- A single run can be validated offline from artifacts + run log.
### M3 — Content systems (bibliography + evidence tracking)
**Artifacts**
- `outputs/bibliography_system_v1.md` — citation/notes format, source quality rubric, and how sources map to claims.
- `outputs/evidence_register_v1.csv` — minimal tabular index: claim_id, source_id, quote, location, confidence.

**Acceptance criteria**
- Every claim in narrative outputs can reference an evidence row.
- Register is machine-readable and stable (fixed columns, no free-form schema drift).
- Clear rules for handling duplicates, uncertain provenance, and conflicting sources.
### M4 — Data model + schemas for deterministic generation
**Artifacts**
- `outputs/data_model_v1.md` — entities, fields, and relationships used by scripts.
- `outputs/schemas_v1/` (if directories are later authorized) or `outputs/schemas_v1.md` — JSON schema snippets embedded in Markdown.

**Acceptance criteria**
- Data model enumerates required/optional fields and allowed values.
- Schemas are sufficient to validate inputs/outputs programmatically.
- Backward-compatible versioning rules are defined.
### M5 — QA and acceptance test suite definitions
**Artifacts**
- `outputs/acceptance_tests_v1.md` — test cases and how to run them.
- `outputs/quality_gate_v1.md` — thresholds and failure conditions.

**Acceptance criteria**
- Tests cover: path constraints, no placeholders, schema validation, and reproducible file ordering.
- Quality gate states objective pass/fail conditions (e.g., “no missing required metadata”).
- Includes at least one negative test example (what should fail).
### M6 — Release packaging and changelog discipline
**Artifacts**
- `outputs/changelog_v1.md` — dated entries with artifact diffs summary.
- `outputs/release_checklist_v1.md` — steps to produce a release bundle.

**Acceptance criteria**
- Changelog entries reference artifact filenames and describe intent of change.
- Release checklist includes: verify run log, verify acceptance tests, verify hashes, bundle outputs.
## Naming conventions (planned)
- **Versioning**: `*_v1.md`, `*_v2.md` for meaningful structural revisions; minor edits stay within the current version unless they break acceptance criteria.
- **Type hints**: prefer descriptive names (e.g., `evidence_register_v1.csv`, `run_log_v1.jsonl`).
- **Stability**: once introduced, filenames remain stable; replacements get a new versioned filename.

## Acceptance criteria for this roadmap artifact (`outputs/roadmap_v1.md`)
- Clearly enumerates milestones M0–M6 with artifact lists and acceptance criteria.
- Contains no placeholders and no references to unbounded future work without criteria.
- Enables an implementer to decide “done/not done” per milestone using only this document.
