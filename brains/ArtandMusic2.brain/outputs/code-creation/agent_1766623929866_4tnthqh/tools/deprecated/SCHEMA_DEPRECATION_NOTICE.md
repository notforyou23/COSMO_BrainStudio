# Schema & Tool Deprecation Notice (Single Blessed Metadata Workflow)

This repository previously accumulated multiple overlapping JSON Schemas and validation scripts for “case study metadata”. To eliminate drift and inconsistent validation results, the project now supports **exactly one authoritative schema** and **one authoritative validator/CLI entrypoint**.
## ✅ Authoritative (“blessed”) replacements

### Schema (single source of truth)
- **schemas/METADATA_SCHEMA.json**

This is the only schema that defines the required/optional fields, types, allowed values, and structure for case study metadata.

### Tooling (single entrypoint)
- **tools/metadata_cli.py**

This is the only supported interface for:
- scaffolding a new metadata file
- validating metadata against the authoritative schema
- generating validation/report outputs in a consistent way
## ❌ Deprecated schemas (do not use)

All metadata schemas other than **schemas/METADATA_SCHEMA.json** are deprecated.

Common legacy names/locations that are now deprecated include (examples):
- schemas/metadata_schema.json
- schemas/metadata.schema.json
- schemas/case_study_metadata.schema.json
- schemas/CASE_STUDY_SCHEMA.json
- tools/schemas/*.json
- any schema embedded inside notebooks, scripts, or copied into case study folders

**Policy:** if it is not exactly `schemas/METADATA_SCHEMA.json`, treat it as legacy and migrate.
## ❌ Deprecated scripts/entrypoints (do not use)

All standalone validators and schema-check scripts are deprecated in favor of **tools/metadata_cli.py**.

Common legacy names/locations that are now deprecated include (examples):
- tools/validate_metadata.py
- tools/validator.py
- tools/metadata_validator.py
- tools/validate_schema.py
- tools/check_metadata.py
- ad-hoc commands that call jsonschema directly against an older schema file

**Policy:** if it is not `python -m tools.metadata_cli ...` (or equivalent invocation of `tools/metadata_cli.py`), treat it as legacy.
## Migration guide (from legacy schema/script to the blessed workflow)

### 1) Stop referencing legacy schema files
If you have any config, docs, or scripts that point to an older schema path, update them to:
- `schemas/METADATA_SCHEMA.json`

### 2) Replace direct validation calls with the CLI
Replace patterns like:
- “run a custom script that loads a schema file and validates JSON”
- “call jsonschema with a legacy schema path”

With the blessed entrypoint:
- `python -m tools.metadata_cli validate <path-to-metadata.json>`

(Exact subcommands/flags are defined by the CLI; the key requirement is: **use metadata_cli.py as the entrypoint**.)

### 3) Regenerate/scaffold metadata using the CLI (optional but recommended)
If your metadata files were created from a legacy template, re-scaffold or reformat using:
- `python -m tools.metadata_cli scaffold ...`

Then re-run validation until it passes.

### 4) Fix validation differences
If validation results change after migration, assume the legacy schema/tool was either:
- incomplete (allowed invalid metadata), or
- divergent (rejected valid metadata)

The authoritative behavior is whatever **schemas/METADATA_SCHEMA.json** enforces.

### 5) Remove or quarantine legacy files
To avoid future accidental use:
- delete deprecated schemas/scripts, or
- keep them under `tools/deprecated/` with clear “DO NOT USE” notes, and ensure no docs/automation reference them.
## Compatibility notes

- The authoritative schema is intended to be used everywhere the repository expects case study metadata.
- Any downstream tooling should import/load the schema via the shared loader (if present) rather than hard-coding paths.
- Validation/reporting should be routed through **tools/metadata_cli.py** to ensure consistent behavior across environments.

If you find a workflow or document that references any other schema or validator, update it to the replacements listed above.
