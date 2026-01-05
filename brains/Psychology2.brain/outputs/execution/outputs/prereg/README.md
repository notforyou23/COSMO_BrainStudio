# /outputs/prereg — Preregistration artifacts

This folder stores preregistration documents and their supporting materials for studies/analyses run in this project. The goal is to make each prereg (a) easy to find, (b) unambiguous about what was planned vs. what changed, and (c) reproducible from the recorded environment, inputs, and code snapshot.
## What belongs here

Include:
- Preregistration documents (PDF/Markdown/HTML).
- Locked analysis plans, decision logs, and deviation notes tied to a prereg.
- Supplementary prereg materials (power calcs, simulated data, pilot summaries) if referenced by the prereg.
- Exported registry receipts or confirmation pages (if applicable).

Do not include:
- Raw data dumps (store under the project’s data area).
- Large intermediate artifacts (store under `/outputs/tools` with run metadata).
## Required contents per prereg package

Each prereg should have, at minimum:
1) A human-readable prereg document (PDF or Markdown).
2) A machine-readable metadata file (`meta.json`) capturing the key fields below.
3) If deviations occur: a deviation log describing what changed and why.

Recommended `meta.json` fields:
- `prereg_id` (string; matches the package folder name)
- `title`
- `authors` (list of names/ids)
- `date_created` (YYYY-MM-DD)
- `registry` (e.g., OSF/AsPredicted/local) and `registration_url` (if any)
- `analysis_scope` (short text)
- `inputs` (paths or dataset identifiers; include versions/hashes when available)
- `code_ref` (git commit hash or archive identifier)
- `status` (`draft` | `submitted` | `registered` | `superseded`)
- `supersedes` (optional prereg_id)
- `notes` (optional)
## Naming & versioning rules

### Folder naming (preferred)
Create one folder per prereg using:

`PREREG-YYYYMMDD_<shortslug>_vMAJOR.MINOR/`

Examples:
- `PREREG-20260115_attention-checks_v1.0/`
- `PREREG-20260203_meta-analysis-alpha_v2.1/`

Rules:
- `YYYYMMDD` is the initial draft/creation date (not necessarily registration date).
- `<shortslug>` is lowercase, ASCII, hyphen-separated, no spaces.
- Use semantic-ish versioning:
  - MAJOR: breaking conceptual changes (new hypotheses/outcomes/analysis family).
  - MINOR: clarifications, tightened thresholds, added robustness checks.
  - Patch versions may be used inside filenames if needed (e.g., `v1.2.1`), but keep folder versions stable once registered.

### File naming within a prereg folder
Use consistent names so automation can find files:
- `prereg.md` or `prereg.pdf` (primary document)
- `meta.json` (required)
- `deviations.md` (only if deviations occur)
- `appendix.<ext>` (optional supporting material)

If multiple formats exist, keep one as canonical (declare in `meta.json` under `canonical_file`).
## Registration, freezing, and updates

- If registered externally, store a copy of the exact submitted content (PDF export or saved HTML) and record the `registration_url`.
- Once registered, do not overwrite the registered prereg document. Instead:
  - Create a new folder with an incremented version, or
  - Add a dated deviation entry in `deviations.md` if the prereg stays the same but execution diverges.
- If a prereg is superseded, set `status: "superseded"` and record `supersedes`/`superseded_by` in metadata (as applicable).
## Deviations policy (minimal)

When analysis differs from prereg, document deviations as:
- What changed (specific variable/model/threshold/outcome).
- Why it changed (data issues, prereg ambiguity, peer review, feasibility).
- When it changed (date).
- Whether it was decided before looking at outcomes (if relevant).

Keep deviations factual and auditable; avoid retroactive rationalization.
## Reproducibility expectations

A prereg package should make it possible to reconstruct what was planned and to trace execution:
- Reference exact inputs (dataset versions, hashes, or immutable IDs).
- Reference the code state (git commit hash or archived snapshot).
- Ensure paths in `meta.json` are relative to the repository root where possible.

If the prereg relies on tool outputs, link to corresponding `/outputs/tools/...` runs and include run IDs in `meta.json`.
