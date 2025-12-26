# add_case_study CLI + Case Study Metadata Schema (Usage)

This project standardizes “case studies” as:
- **Machine-readable metadata**: a JSON file validated against `schemas/METADATA_SCHEMA.json`
- **Human narrative**: a Markdown file for the write-up

The CLI `add_case_study` creates both stubs and validates the JSON stub against the schema (no network activity; no downloads).
## Quickstart

1) Create a new case study:
- `python -m src.add_case_study --id <case_study_id> --title "<Title>" --out outputs/case_studies/`

2) This writes:
- `outputs/case_studies/<case_study_id>.json` (metadata; must validate)
- `outputs/case_studies/<case_study_id>.md` (narrative stub)

3) Validate an existing metadata file:
- `python -m src.add_case_study --validate outputs/case_studies/<case_study_id>.json`

Notes:
- Filenames and `id` should be stable, URL-safe, and lowercase (e.g., `urban_heat_mitigation_2022`).
- The CLI populates a canonical JSON stub template and fails fast with actionable validation errors.
## Directory layout (expected)

- `schemas/METADATA_SCHEMA.json` — JSON Schema for case-study metadata
- `src/utils/schema_validate.py` — loads schema and validates JSON with clear errors
- `src/templates/case_study.stub.json` — canonical metadata stub template
- `src/templates/case_study.stub.md` — canonical narrative stub template
- `outputs/case_studies/` — where new case studies are written
## Metadata model overview

Each case study is described by a single JSON document. The schema enforces:
- **identity** (id, title, versioning)
- **summary** (what happened, where/when, outcomes)
- **methods/data** (how results were obtained)
- **provenance** (who authored/curated and when)
- **sources** with **authoritative URLs** (no downloaded artifacts stored here)
- **rights/licensing** (what can be reused, and under what terms)

The JSON should be treated as the authoritative index; the Markdown is the narrative companion.
## Field guide (schema-oriented)

Exact field names are defined in `schemas/METADATA_SCHEMA.json`. Common top-level groups:

### Identification
- `id` (string, required): stable unique identifier; matches filename stem.
- `title` (string, required): human-readable title.
- `type` (string): e.g., `case_study`.
- `version` / `schema_version` (string): optional version indicators for change tracking.

### Summary & context
- `abstract` or `summary` (string, required/optional per schema): a concise description.
- `tags` (array of strings): keywords for search/filtering.
- `domain` / `topics` (array): thematic categorization.

### Geography & time
- `location` (object): may include `name`, `country`, `admin_levels`, and/or `geometry` references.
- `timeframe` (object): may include `start_date`, `end_date`, and notes.

### Methods & evidence
- `methods` (string/array): high-level approach.
- `data_sources` (array): datasets, reports, or systems used (referenced by URL; see “Authoritative URLs”).
- `metrics` / `outcomes` (array/object): what was measured and what changed.

### Provenance
- `authors` / `maintainers` (array): people or organizations responsible for this metadata.
- `created` / `updated` (date-time): timestamps in ISO-8601 format.
- `contact` (object): optional point of contact.
## Rights & licensing (required and non-negotiable)

Every case study MUST state rights clearly so downstream users know what they can do.

The schema includes a dedicated rights block (name may be `rights`, `licensing`, or similar per schema), typically covering:
- **License identifier** (required): Prefer SPDX license IDs (e.g., `CC-BY-4.0`, `CC-BY-SA-4.0`, `MIT`).
- **License URL** (required): a canonical URL describing the license terms.
- **Rights holder** (required): person/org that owns the content being described (metadata and/or referenced materials).
- **Usage notes / restrictions** (optional but recommended): any limitations, attribution requirements, or exceptions.

Rules:
- Do not write “unknown”, “TBD”, or omit licensing. If uncertain, pick a conservative label such as
  “All rights reserved” with a rights-holder and provide a contact or citation explaining the uncertainty.
- Licensing in the metadata describes the *case-study content you provide* (metadata and narrative) and should
  not misrepresent third-party sources. Third-party sources must be cited and linked, not copied in.
## Authoritative URLs (required; no downloads)

Sources MUST be referenced via authoritative URLs. The CLI and schema are designed to avoid bundling external content.

What qualifies as “authoritative”:
- Official publisher pages (government, journal, standards body, organization site)
- DOI landing pages (preferred for scholarly works)
- Dataset landing pages from recognized repositories (e.g., Zenodo, Figshare, institutional repositories)
- Official project documentation pages

What to avoid:
- Random mirrors, scraped PDFs, or unverified re-uploads
- Link shorteners when the canonical URL is available

Best practice for each source entry:
- `title`
- `publisher`/`organization`
- `url` (authoritative)
- `accessed` date (ISO-8601)
- Optional: `doi`, `citation`, `license` for that specific source if known

Rule of thumb: link to the page that *explains and hosts* the artifact, not a transient direct-download link.
## CLI behavior (what it enforces)

When you run `add_case_study`, it:
1) Creates a JSON stub from `src/templates/case_study.stub.json`
2) Creates a Markdown stub from `src/templates/case_study.stub.md`
3) Inserts provided values (e.g., `id`, `title`, timestamps)
4) Validates the JSON against `schemas/METADATA_SCHEMA.json`
5) Fails with readable validation errors that point to the JSON path and explain the constraint

Validation examples of what can fail:
- Missing required fields (e.g., `id`, `title`, rights/license block)
- Invalid URL formats or missing authoritative URL fields for sources
- Wrong types (string vs array/object)
- Invalid date-time format
## Example invocation patterns

Create:
- `python -m src.add_case_study --id coastal_flooding_2021 --title "Coastal Flooding Response (2021)" --out outputs/case_studies/`

Validate:
- `python -m src.add_case_study --validate outputs/case_studies/coastal_flooding_2021.json`

Tip:
- Treat the JSON file as the contract. Update the Markdown narrative freely, but keep metadata consistent
  and re-run validation when metadata changes.
## Editing workflow

1) Run the CLI to create stubs.
2) Fill in the JSON metadata first (especially rights/licensing and sources with authoritative URLs).
3) Re-run validation until clean.
4) Write the narrative in the Markdown file; add citations that match the sources in JSON.

If validation fails, read the error message from `schema_validate.py`; it should include the JSON path and what to change.
