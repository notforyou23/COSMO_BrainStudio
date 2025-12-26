# Case-study catalog (outputs/catalog/)

This directory stores **validated case-study entries** as JSON plus a **catalog index** that lists/points to them. Entries are intended to be machine-readable and schema-validated via the project CLI.

## Directory layout

- `outputs/catalog/`
  - `index.json` — catalog index (list of all case studies; generated/updated by the CLI)
  - `case-studies/`
    - `<id>.json` — one case-study entry per file (created/updated by the CLI)

Related (outside this directory):
- `schemas/case-study.schema.json` — canonical schema for a single case study
- `schemas/catalog.schema.json` — canonical schema for `outputs/catalog/index.json`
- `src/catalog_cli.py` — CLI to add/validate entries and maintain the index

## Case study entry: required fields (high level)

Each `case-studies/<id>.json` must satisfy `schemas/case-study.schema.json`. At a minimum, expect:

- `id` (string): stable identifier (slug-like; used as filename)
- `title` (string)
- `summary` (string): concise description
- `tags` (array of strings): topical tags/keywords
- `metadata` (object): descriptive fields such as:
  - `date` (ISO-8601 string, e.g., `2025-12-24`)
  - `authors` (array of strings) and/or `organization`
  - `geography` / `sector` (strings, if applicable)
- `citations` (array of objects): sources that support claims in the case study; typical fields:
  - `type` (e.g., `url`, `doi`, `isbn`, `report`)
  - `title`
  - `url` and/or other identifiers
  - `accessed` (ISO-8601 date) when applicable
- `rights` (object): provenance and permissions, typically including:
  - `license` (e.g., `CC-BY-4.0`, `All Rights Reserved`)
  - `copyright_holder`
  - `usage_notes` (optional)

The schema is the authority: if a field is missing or wrong type/format, validation will fail.

## Catalog index

`outputs/catalog/index.json` is an inventory of all case studies under `outputs/catalog/case-studies/`. The CLI updates this file automatically when you add a case study, and validation checks that:
- all referenced case-study files exist
- each case study validates against the case-study schema
- the index validates against `schemas/catalog.schema.json`

## Using the CLI

Run from the repository root (or wherever `src/` and `schemas/` are available):

Validate everything:
- `python src/catalog_cli.py validate`

Add a new case study (interactive prompts or flags, depending on implementation):
- `python src/catalog_cli.py add --title "..." --summary "..." --tags tag1,tag2 --license CC-BY-4.0`

Validate a single entry file:
- `python src/catalog_cli.py validate --case outputs/catalog/case-studies/<id>.json`

Common workflow:
1) `add` to create `case-studies/<id>.json` and update `index.json`
2) `validate` to ensure schema compliance before committing or publishing

## Conventions

- Filenames are derived from `id` and should be stable over time.
- Prefer short, consistent tags (lowercase, hyphenated if multiword).
- Citations should be sufficient for a third party to locate the source.
- Rights fields must be explicit; do not assume “fair use” or default permissions.

If validation fails, fix the JSON to match the schema and rerun `validate`.
