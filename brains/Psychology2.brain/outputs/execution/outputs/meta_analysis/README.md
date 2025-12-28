# /outputs/meta_analysis

This folder contains **meta-level analysis artifacts**: summaries, audits, comparisons, evaluation notes, and synthesis documents produced by the CLI/tooling to explain *how* results were obtained and *how reliable/consistent* they are.

## What belongs here
Include artifacts that analyze or validate other outputs (e.g., taxonomy, extracted entities, summaries), such as:
- consistency reviews across cycles/runs (agreement/divergence, deltas)
- rubric-based evaluations and scoring reports
- error analyses, edge-case notes, limitations, and risk assessments
- cross-source comparison matrices and reconciliation notes
- run summaries that explain decisions (filters, thresholds, exclusions)

Do **not** place primary deliverables here (taxonomies, final datasets, end-user reports). Those belong in their dedicated folders.

## Expected file types
Preferred formats (in order):
- Markdown: `*.md` for narrative analyses and human-readable reports
- JSON: `*.json` for structured metrics, scores, and machine-readable summaries
- CSV: `*.csv` for tabular comparisons or per-item evaluations

Avoid binary formats. If you must include an attachment, prefer a text representation (e.g., CSV over XLSX).

## Naming conventions
Use stable, sortable names:
- `YYYY-MM-DD_<topic>_<kind>.md` (recommended)
- Or cycle/run oriented: `cycle_<N>_<topic>_<kind>.md`
- If multiple variants exist, append a short suffix: `_v2`, `_alt`, `_ablationA`

Examples:
- `2025-12-26_taxonomy_consistency_review.md`
- `cycle_39_extraction_error_analysis.md`
- `2025-12-26_rubric_scores.json`

## Minimal metadata requirements
Every artifact in this folder MUST include traceability metadata.

### For Markdown files
Include a front-matter-like header near the top (YAML style is acceptable but not required). At minimum provide:
- `title`: concise name
- `created_at`: ISO-8601 timestamp (UTC preferred)
- `source_inputs`: list of referenced files/ids (relative to `/outputs` when possible)
- `method`: short description of approach (rubric, diffing strategy, model/prompt, heuristics)
- `scope`: what is covered and what is excluded
- `authoring_agent`: tool/agent name (if applicable)

Recommended additional fields:
- `cycle`: integer cycle number (if the system is cycle-based)
- `tool_version`: CLI/tool version
- `parameters`: key settings (thresholds, sampling, temperature, etc.)
- `hashes`: optional content hashes for key inputs (sha256)

### For JSON files
Top-level object MUST contain:
- `meta`: object with at least the fields listed above (as applicable)
- `results`: the primary structured payload (metrics, per-item entries, aggregates)

### For CSV files
Provide an adjacent Markdown sidecar with the same base name:
- `example.csv` + `example.md` (metadata + column definitions)

## Content standards
- Be explicit about assumptions, uncertainty, and known failure modes.
- Prefer reproducible descriptions: include enough detail to rerun the analysis.
- Keep references stable: use relative paths like `outputs/taxonomy/...`.
- If reporting metrics, define them (formula/meaning) and list the evaluation set.

## Update discipline
- Meta-analysis artifacts should be additive and historical; avoid overwriting unless correcting an error.
- When a correction is made, create a new artifact (or append a clearly dated correction section) and ensure the project changelog is updated by the CLI in its normal workflow.

## Checklist (quick)
- [ ] File is in the right folder and is not a primary deliverable
- [ ] Name is sortable and descriptive
- [ ] Minimal metadata included (traceability)
- [ ] Inputs referenced with stable paths/ids
- [ ] Method and scope clearly stated
- [ ] Structured outputs (if any) are machine-readable and documented
