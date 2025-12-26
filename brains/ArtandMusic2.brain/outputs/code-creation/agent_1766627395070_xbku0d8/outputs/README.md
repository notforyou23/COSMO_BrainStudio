# /outputs

This directory is the project’s **single source of truth for generated deliverables** (reports, case studies, schemas, and supporting logs). Treat everything here as publishable unless explicitly marked otherwise.

## What belongs here

The scaffold generator (or a manual bootstrap) should ensure the following core artifacts exist:

- `REPORT_OUTLINE.md` — Canonical structure for the main report deliverable (sections, required evidence, and narrative flow).
- `CASE_STUDY_TEMPLATE.md` — Standard template for documenting individual case studies consistently (context → method → results → limitations).
- `METADATA_SCHEMA.json` (and/or other `METADATA_SCHEMA.*`) — Machine-readable schema describing required metadata fields for outputs (provenance, sources, dates, versions, and rights).
- `RIGHTS_AND_LICENSING_CHECKLIST.md` — Human-readable checklist to ensure permissions, attribution, and license compatibility are verified for any third-party material.
- `RIGHTS_LOG.csv` — Line-by-line log of external assets and permissions (e.g., figures, images, datasets, quotes), including where they were obtained and how they may be used.

If additional files are generated, they should be **deterministic, attributable, and reproducible** from inputs and configuration.

## Rights & licensing (required)

Any output that incorporates third-party content (images, charts, datasets, excerpts, trademarks, or distinctive designs) must be tracked and cleared before distribution.

- Use `RIGHTS_AND_LICENSING_CHECKLIST.md` to confirm compliance steps were completed.
- Use `RIGHTS_LOG.csv` to record each external item and its usage terms.
- Outputs should reference these tracking files when relevant (e.g., in acknowledgements, footnotes, appendix, or a “Rights & Licensing” section).

## Recommended workflow

1. Initialize (or validate) the scaffold so the expected files exist.
2. Draft content using `REPORT_OUTLINE.md` and `CASE_STUDY_TEMPLATE.md`.
3. Maintain structured metadata in `METADATA_SCHEMA.*` and keep it in sync with published outputs.
4. Before sharing externally, complete the checklist and update the rights log for every third-party asset used.

## Conventions

- Prefer descriptive, stable filenames.
- Keep generated artifacts in `/outputs` and source code in `/src`.
- Avoid embedding secrets or private data in any file under `/outputs`.
