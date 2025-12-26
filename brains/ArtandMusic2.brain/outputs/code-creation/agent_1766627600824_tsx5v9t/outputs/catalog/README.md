# Case-study catalog (`outputs/catalog/`)

This directory defines the *contract* for case studies stored under `outputs/case_studies/` by providing a shared JSON Schema and documentation for the CLI that creates/validates/indices those records.

The goals are:
- Consistent, machine-validated case study documents
- Deterministic indexing for discovery and tooling
- A stable interface for downstream consumers (UI, search, pipelines)
## Required files in this directory

### `METADATA_SCHEMA.json`
A JSON Schema (Draft 2020-12 or compatible) that defines:
- The top-level metadata format used by the catalog/tooling
- The required shape of each case study document written to:
  `outputs/case_studies/<slug>/case_study.json`

The schema is intended to be:
- Strict enough to catch missing/invalid fields early
- Stable and versioned (include an explicit schema version field in documents)
- Compatible with common validators (e.g., `jsonschema` in Python)
## Case study storage layout (output)

Case studies live outside this folder, under:

- `outputs/case_studies/<slug>/case_study.json` (the canonical record)
- `outputs/case_studies/index.json` (a catalog index for fast listing)

Recommended layout example:

outputs/
  case_studies/
    index.json
    attention-switching/
      case_study.json
    measurement-equity/
      case_study.json
## `case_study.json` expectations

Each `case_study.json` should:
- Validate against `outputs/catalog/METADATA_SCHEMA.json`
- Use a filesystem-safe `slug` that matches its folder name
- Include stable identifiers and timestamps (created/updated) if the schema requires them
- Prefer normalized, portable values (UTC timestamps, lowercase slugs, explicit versions)

If your schema supports it, include:
- `schema_version` (or equivalent)
- `title`, `summary`, `tags`
- `sources` / `artifacts` entries with relative paths where possible
## Index file (`outputs/case_studies/index.json`)

The index is a lightweight listing to avoid scanning all folders each time.
Typical properties:
- Contains one entry per case study (at minimum: `slug`, `title`, `path`, and `updated_at`)
- Is written deterministically (sorted by slug or updated time)
- Is updated atomically to avoid partial writes on interruption (write temp + rename)

Downstream tools should treat `index.json` as the primary listing surface and the per-slug `case_study.json` as the source of truth.
## CLI workflow (authoring)

A small CLI is provided at `src/cli/add_case_study.py` that:
1. Accepts user inputs (e.g., `--slug`, `--title`, `--summary`, tags, links, etc.)
2. Writes `outputs/case_studies/<slug>/case_study.json`
3. Validates the new document against `outputs/catalog/METADATA_SCHEMA.json`
4. Updates `outputs/case_studies/index.json` safely and deterministically

Typical usage (example):

python -m src.cli.add_case_study \
  --slug attention-switching \
  --title "DMN↔ECN switching for creative work" \
  --summary "A case study describing context-gated control for generate/evaluate phases." \
  --tags creativity cognition control
## Validation & interoperability

The CLI relies on shared helpers (for context):
- `src/catalog/schema.py`: load schema + validate JSON documents
- `src/catalog/index.py`: read/update/write the index in a stable, safe way

If you add fields to the schema:
- Update `METADATA_SCHEMA.json` first
- Ensure existing case studies still validate (or bump schema/document version and migrate)
- Keep field names consistent and documented to support automation
