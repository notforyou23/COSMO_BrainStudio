# /outputs Artifact Rules (Deliverables Audit)

This folder contains **tangible artifacts** produced by the project. The deliverables audit checks for real files here; keep contents stable, specific, and reviewable.

## 1) What counts as an artifact
An artifact is a file that:
- is stored directly in `/outputs/` (not elsewhere),
- has meaningful, non-placeholder content,
- is understandable without external context,
- can be reviewed for completeness (e.g., includes source, date, and status where applicable).

Examples: research notes, templates, summaries, decision logs, exported datasets, diagrams (as images), or small scripts **only if** they are themselves the deliverable.

## 2) File naming and organization
- Put deliverables **at the top level** of `/outputs/` unless there is a clear need for subfolders.
- Use lowercase with underscores: `research_template.md`, `first_artifact.md`.
- Prefer stable names over timestamps. If multiple versions are required, suffix with `v1`, `v2`, etc.
- Do not overwrite prior artifacts unless the goal explicitly requires replacement.

## 3) Required metadata (for markdown artifacts)
Markdown artifacts should start with a small header block containing:
- **Title**
- **Created (YYYY-MM-DD)**
- **Owner/Author**
- **Purpose**
- **Status**: `draft` | `in_review` | `final`
- **Sources** (if any): citations or links
- **Verification** (if applicable): what was checked and what remains unverified

## 4) Source handling and citations
- Every factual claim that depends on external information should have a **source**.
- Prefer primary sources; otherwise cite reputable secondary sources.
- Use consistent citation style (e.g., inline links or a “Sources” section with numbered references).
- When uncertain, mark the claim as **unverified** rather than asserting it as fact.

## 5) Quality bar (no placeholders)
Artifacts must **not** contain:
- “TODO”, “TBD”, “lorem ipsum”, or empty sections meant to be filled later,
- vague statements without specifics when specifics are expected (e.g., “add citations later”),
- dead links presented as sources (if a link is required, include access date or mirror notes).

If something cannot be completed, write a short explanation and mark the status accordingly (e.g., `draft`)—but still provide a useful, reviewable artifact.

## 6) Reproducibility & traceability
Where relevant, include:
- assumptions,
- steps taken,
- inputs/outputs,
- and enough detail for another person to reproduce the result.

For research notes, use the standardized template in `research_template.md` (created separately) and include verification status per claim.

## 7) Allowed formats
- Preferred: `.md` (Markdown) for human review.
- Also acceptable: `.txt`, `.csv`, `.json`, `.png`, `.pdf` when appropriate.
- Avoid binary formats unless necessary; if used, include a short `.md` companion note describing how it was produced.

## 8) Review checklist (quick)
Before considering an artifact “done”, confirm:
- [ ] File is in `/outputs/` and has a stable name
- [ ] Purpose and status are stated
- [ ] Claims are sourced or explicitly marked unverified
- [ ] No placeholders or empty sections
- [ ] Content is understandable on its own

--- 
This README defines the conventions for artifacts in `/outputs/` to ensure deliverables audits detect real, reviewable work products.
