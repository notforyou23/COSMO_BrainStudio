# /outputs — Artifact Rules

This folder contains **deterministic, auditable deliverables** produced each cycle. Every cycle must “ship” at least one concrete artifact here.

## Core principles
- **Deterministic**: Artifacts must be reproducible from committed inputs and code for the same cycle.
- **Auditable**: Each artifact states scope, assumptions, and how it was produced/validated.
- **Atomic**: One file = one deliverable purpose (avoid mixed, sprawling documents).
- **No placeholders**: No “TBD”, “TODO”, “coming soon”, or empty sections.
- **Stable paths**: Never rename/move artifacts unless there is a compelling reason and a migration note.

## Required header (top of every artifact)
Include a short front-matter style header (plain Markdown is fine) with:
- **Title**
- **Version** (e.g., v1, v1.1)
- **Date** (ISO-8601)
- **Owner/Agent** (who generated it)
- **Inputs** (source files, prompts, datasets)
- **Method** (how it was produced)
- **Acceptance criteria** (what “done” means for this artifact)

## Naming conventions
Use lowercase snake_case with an explicit version suffix:
- `name_v1.md`, `name_v2.md`
- If the artifact is time-scoped: `name_YYYY-MM-DD_v1.md`
- If the artifact is a report: `report_<topic>_v1.md`
- If the artifact is machine-readable: prefer `.json` / `.csv` with versioned names.

Avoid:
- spaces, uppercase, `final`, `latest`, or ambiguous names like `notes.md`.

## Versioning rules
- **v1**: first complete, reviewable deliverable (not a draft).
- **Minor bump** (v1.1, v1.2): clarifications, formatting, small fixes.
- **Major bump** (v2): changes in scope, structure, or acceptance criteria.

## Change control
- Each cycle should add or update **only what is necessary**.
- When updating an existing artifact, append a short “Changelog” section at the bottom.

## Quality bar
Artifacts must be:
- internally consistent (no contradictions within the file),
- precise about scope (what is included/excluded),
- easy to verify (clear criteria and, when relevant, commands or checks).

## “Ship every cycle” checklist
Before ending a cycle, confirm:
1. **At least one artifact** in `/outputs/` was created or meaningfully updated.
2. Artifact filename follows naming conventions and includes a version.
3. Artifact includes the required header fields.
4. No placeholders/TODOs; all sections are complete.
5. Acceptance criteria are explicit and satisfied.
6. If applicable, validation steps/results are recorded (briefly).
7. Paths referenced are relative and stable (prefer `/outputs/...`).
8. Output is deterministic (no nondeterministic timestamps inside content unless required).
9. Directory state is logged (file list captured by the run output).
