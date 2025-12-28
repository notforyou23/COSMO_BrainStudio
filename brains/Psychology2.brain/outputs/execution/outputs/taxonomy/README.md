# /outputs/taxonomy

## Purpose
This folder contains *taxonomies* used by the project: stable, human-auditable classification systems (labels, codes, hierarchies, and mappings) that other outputs reference.

A taxonomy here is a source of truth for:
- controlled vocabularies (allowed values)
- hierarchical category trees (parent/child)
- crosswalks/mappings (old->new, external->internal)
- definitions/notes needed to apply the taxonomy consistently

## What belongs here
Include:
- Canonical taxonomy files (YAML or JSON) used by the CLI/tooling to label or validate outputs
- Mapping tables/crosswalks (CSV allowed when tabular is clearer)
- Documentation explaining semantics, invariants, and change history relevant to users

Exclude (belongs elsewhere):
- Analyses that *use* the taxonomy (put in `/outputs/meta_analysis/`)
- Tooling code (put in `/outputs/tooling/`)
- One-off experimental label sets that are not intended for reuse

## File and naming conventions
- Prefer: `kebab-case` for file names and folder names.
- Canonical taxonomy file name pattern:
  - `taxonomy.<name>.<major>.<minor>.yaml` or `.json`
  - Example: `taxonomy.issues.1.2.yaml`
- Crosswalk/mapping pattern:
  - `crosswalk.<from>_to_<to>.<major>.<minor>.csv|yaml|json`
- If a single taxonomy must be split across files, use a folder:
  - `taxonomy.<name>.v<major>.<minor>/...` with an `index.yaml|json` entrypoint.

## Canonical schema conventions
Canonical taxonomy files SHOULD be YAML or JSON and MUST contain:

Top-level fields:
- `schema_version`: string (e.g., `"1.0"`) for this taxonomy-file schema (not the taxonomy content version)
- `taxonomy`:
  - `name`: string (machine-safe, e.g., `"issues"`)
  - `title`: string (human-friendly)
  - `version`: string (semantic-ish, e.g., `"1.2"`)
  - `status`: `"draft"` | `"active"` | `"deprecated"`
  - `updated`: ISO-8601 date or datetime
  - `description`: string
  - `nodes`: array of node objects (see below)
  - `constraints` (optional): object describing validation rules

Node object fields:
- `id`: string (stable identifier; MUST NOT be reused for different meanings)
- `label`: string (display label)
- `description` (optional): string
- `parent_id` (optional): string (for hierarchies; root nodes omit)
- `aliases` (optional): array of strings
- `tags` (optional): array of strings
- `deprecated` (optional): boolean
- `replaced_by` (optional): string (node id)
- `examples` (optional): array of strings

Required invariants:
- `id` values are unique within the taxonomy.
- If `parent_id` is present, it references an existing node id.
- Prefer stable ids (do not encode volatile ordering); labels may evolve.
- Deprecations MUST preserve the old node id and indicate `deprecated: true` plus `replaced_by` when applicable.

## Compatibility and versioning rules
- Use `taxonomy.version` as the content version.
- Backward-compatible changes (minor): adding new nodes, adding aliases, clarifying descriptions.
- Potentially breaking changes (major): renaming ids, removing nodes, changing hierarchy in a way that invalidates prior assignments.
- Never silently change meanings: if semantics change, deprecate the old node and introduce a new one.

## How the CLI/tool should use these files
- Treat canonical taxonomy files as read-only inputs for classification/validation.
- When writing outputs that reference taxonomy nodes, record the `taxonomy.name`, `taxonomy.version`, and the node `id` (not label) wherever possible.

## Recording updates in /outputs/CHANGELOG.md
Any change under `/outputs/taxonomy/` MUST be recorded immediately in `/outputs/CHANGELOG.md` with:
- cycle identifier (same cycle that produced the change)
- what changed (created/updated/deprecated), including file path(s)
- taxonomy name and content version
- whether the change is breaking (major) or non-breaking (minor)
- brief rationale (1–3 sentences)

Suggested entry format (example):
- taxonomy: issues v1.3 (non-breaking) — added nodes `X`, `Y`; updated aliases for `Z`; files: `outputs/taxonomy/taxonomy.issues.1.3.yaml`.

## Minimal review checklist
- Node ids stable and unique
- Parent references valid; no cycles
- Deprecations include replacement guidance
- Version bumped appropriately
- CHANGELOG entry added for the same cycle
