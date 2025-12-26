# Outputs Directory Guide

This folder is the **single source of truth for audit-ready deliverables** produced by this repository (reports, datasets, figures, logs, and other artifacts). Audits expect files to exist **on disk** under `outputs/` with predictable names and minimal, self-describing metadata.
## What belongs in `outputs/`

Store finalized artifacts that reviewers should verify without re-running code, including:

- Documents: `*.md`, `*.pdf`, `*.html`
- Data exports: `*.csv`, `*.json`, `*.parquet` (keep sizes reasonable)
- Figures: `*.png`, `*.svg`
- Model/run metadata: `*.json`, `*.txt` logs (sanitized; no secrets)

Do **not** store: secrets, API keys, raw credentials, or large ephemeral caches.
## Recommended layout

Use subfolders to keep audits predictable:

- `outputs/reports/` — narrative deliverables (status reports, summaries)
- `outputs/data/` — exported datasets and tables
- `outputs/figures/` — images/plots used in reports
- `outputs/logs/` — run logs and provenance notes
- `outputs/manifests/` — machine-readable indexes of deliverables

This repository may add more subfolders, but keep the intent obvious and consistent.
## Naming conventions (strict)

Prefer deterministic, sortable, and greppable names:

- Use **lowercase** and **kebab-case** (`my-report.md`)
- Avoid spaces; avoid special characters besides `-` and `_`
- Include a **date** when the artifact is time-specific: `YYYY-MM-DD`
- Include a **version tag** when multiple revisions exist: `v1`, `v2`, `v1.1`
- Include a short **scope/topic** label

Examples:
- `reports/2025-12-22-audit-summary-v1.md`
- `data/2025-12-22-metrics-export-v2.csv`
- `figures/2025-12-22-latency-histogram-v1.png`
## Minimum metadata requirements

Every deliverable should be self-describing:

- **Human-readable docs** (`.md/.pdf/.html`) must state on the first page:
  - purpose and scope
  - generation method (manual vs. script; script path if applicable)
  - inputs used (source files/parameters) and any assumptions
  - author/owner (team or role) and creation date
- **Data files** should have either:
  - a companion `*.md` or `*.json` with schema + provenance, or
  - a header row plus a short `README.md` in the same folder describing columns.
- **Figures** should include a caption either embedded in a report or in a companion
  `*.md` stating what the plot shows and what data it is based on.
## Audit expectations (what reviewers check)

Auditors typically verify:

1. **File existence** under `outputs/` (not just described in chat or code)
2. **Reproducibility hints** (how it was produced; inputs and parameters)
3. **Consistency** between filenames, dates, and described versions
4. **No sensitive content**
5. **Completeness**: key deliverables are present (reports + supporting artifacts)

If an audit states “0 files created”, it means nothing tangible was written to disk;
ensure deliverables are committed/generated into this folder.
## How to add a deliverable

1. Choose the correct subfolder (`reports/`, `data/`, `figures/`, `logs/`).
2. Name the file following the convention above.
3. Include the minimum metadata (in-file or companion file).
4. If the deliverable is generated, ensure the generating script writes to `outputs/`.
5. Re-run the workflow and confirm the file exists locally before submission.
## Quick checklist before submission

- [ ] Deliverable file is in `outputs/` and opens correctly
- [ ] Filename matches convention (date/topic/version)
- [ ] Metadata/provenance included
- [ ] No secrets or private data
- [ ] Supporting artifacts (data/figures) referenced by reports are present
