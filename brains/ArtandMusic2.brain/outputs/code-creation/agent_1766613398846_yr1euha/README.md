# Outputs Initializer (Stage 1)

This project provides a small initializer that creates an `outputs/` directory and a set of starter artifacts used to collect and standardize exemplar case studies.

The initializer is designed to be **idempotent** (safe to re-run). It creates missing files/directories and will avoid overwriting existing content unless explicitly instructed by CLI flags (if enabled in your implementation).
## Quick start

From the project root:

- Run as a module:
  - `python -m src.init_outputs`

- Or run the script directly:
  - `python src/init_outputs.py`

Typical optional arguments (if present in your CLI):
- `--project-root PATH` (default: current working directory)
- `--outputs-dir NAME` (default: `outputs`)
- `--dry-run` (print planned writes without modifying the filesystem)
- `--force` (overwrite existing artifacts; use cautiously)

After running, commit the generated artifacts (templates + schema + index) so the team shares a single, stable baseline.
## What gets created under `outputs/`

The initializer creates `outputs/` and these initial artifacts:

1) `outputs/REPORT_OUTLINE.md`
- A report outline you can use to synthesize case studies into a consistent final report.
- Treat this as the canonical structure for reporting (headings, sections, and expected content).

2) `outputs/CASE_STUDY_TEMPLATE.md`
- A Markdown template to author each exemplar in a consistent format.
- New case studies should be created by copying this template and filling it in.

3) `outputs/METADATA_SCHEMA.md` (or `outputs/META.md`)
- Human-readable schema describing the metadata fields required/expected for each case study.
- This schema should match the required columns in the intake CSV and the fields referenced in the case study template.

4) `outputs/CASE_STUDIES_INDEX.csv`
- The single intake table for exemplars.
- Each row is one case study and points to the corresponding authored case study file and supporting artifacts.
## Recommended workflow

1) Initialize:
- Run `python -m src.init_outputs` to ensure `outputs/` and baseline artifacts exist.

2) Add a new case study:
- Copy `outputs/CASE_STUDY_TEMPLATE.md` to a new file under `outputs/` (or a subfolder), e.g.:
  - `outputs/case_studies/CS_0001_example.md`
- Fill out the sections in the Markdown file.

3) Register it in the index:
- Add a row to `outputs/CASE_STUDIES_INDEX.csv` that includes:
  - a stable ID (do not reuse IDs)
  - a title and short summary
  - tags/domains for filtering
  - a pointer to the authored Markdown path
  - provenance (source URL, license/terms, etc.)

4) Synthesize:
- Use `outputs/REPORT_OUTLINE.md` as the structure for summarizing and comparing exemplars.
## How to extend templates

The default artifact contents are expected to live in:
- `src/templates.py`

To customize:
- Edit the default template strings in `src/templates.py`.
- Re-run the initializer to apply changes to new projects or to regenerate artifacts (only if your CLI supports `--force` or if you remove files intentionally).

Good practice:
- Keep templates stable and version-controlled.
- When you change a template, consider whether existing case studies should be migrated or whether the change is only for future entries.
## How to extend the metadata schema

The metadata schema file (`outputs/METADATA_SCHEMA.md` or `outputs/META.md`) should answer:
- Which fields are required vs optional
- Allowed values (enums) for key fields (e.g., domain, status, sensitivity)
- Formatting constraints (e.g., dates in ISO-8601, tags as semicolon-separated)
- Provenance and licensing requirements

When you update the schema:
- Ensure the required columns in `outputs/CASE_STUDIES_INDEX.csv` still match the schema.
- Ensure the case study template references the same field names (to avoid drift).

If you add new fields:
- Add columns to the CSV (with empty values allowed if optional).
- Add a corresponding section or metadata block in the case study template if the field should be authored per case study.
## CSV intake table expectations

The initializer’s CSV utilities are expected to:
- Write a header with required columns
- Use robust quoting to preserve commas/newlines in text fields
- Validate that required columns are present on read

Common, recommended columns:
- `case_study_id` (unique, stable key)
- `title`
- `one_line_summary`
- `domain`
- `tags` (e.g., `tag1;tag2;tag3`)
- `source_url`
- `license`
- `artifact_path` (path to the authored Markdown case study file)
- `created_at` / `updated_at` (ISO-8601)
- `notes`

Keep `CASE_STUDIES_INDEX.csv` as the single source of truth for what exists and where it lives.
## Safety / filesystem notes

The initializer should only write within the project root. Path utilities are expected to:
- Resolve paths safely
- Prevent directory traversal
- Support dry-run behavior where no writes occur

If you run into unexpected overwrites, re-run with `--dry-run` first (if supported) and confirm your configured project root and outputs directory.
