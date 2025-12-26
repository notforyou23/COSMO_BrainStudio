# Tools: Single Blessed Metadata Workflow

This repository uses **one authoritative metadata schema** and **one authoritative CLI**:

- Schema (authoritative): `schemas/METADATA_SCHEMA.json`
- CLI entrypoint (authoritative): `tools/metadata_cli.py` (run as a module)

All scaffolding, validation, and reporting should be done through the CLI below.
## Quick start (recommended workflow)

Run these from the repository root:

1) Scaffold a new metadata file:

    python -m tools.metadata_cli scaffold \
      --out case_studies/<CASE_STUDY_ID>/metadata.json

Expected output:
- Creates `case_studies/<CASE_STUDY_ID>/metadata.json` containing a valid starter structure.
- Prints the path to the created file.

2) Validate metadata against the authoritative schema:

    python -m tools.metadata_cli validate \
      case_studies/<CASE_STUDY_ID>/metadata.json

Expected output:
- Exit code `0` when valid; prints a short “OK”/success message.
- Exit code non-zero when invalid; prints validation errors with JSON pointer-style paths.

3) Validate a directory (all metadata files found under a folder):

    python -m tools.metadata_cli validate \
      --root case_studies

Expected output:
- Scans for metadata JSON files under `case_studies/` (implementation-defined discovery).
- Prints a summary (counts pass/fail) and exits non-zero if any file fails.
## Reporting / inspection

Generate a human-readable report (if supported by the CLI):

    python -m tools.metadata_cli report \
      --root case_studies \
      --format table

Expected output:
- Prints a compact table listing each metadata file and status.
- Non-zero exit if report detects invalid files (same policy as `validate`).
## Schema source of truth

The only schema considered canonical is:

- `schemas/METADATA_SCHEMA.json`

Notes:
- Tooling must load and validate against this file (directly or via a shared loader, e.g. `tools/_schema_loader.py`).
- Any other schema copies/variants should be treated as deprecated and not used for validation.
## Common CLI patterns

Show help:

    python -m tools.metadata_cli --help

Show command help:

    python -m tools.metadata_cli scaffold --help
    python -m tools.metadata_cli validate --help
    python -m tools.metadata_cli report --help

Machine-friendly usage:
- Use exit codes to gate CI (0 = success, non-zero = failure).
- Prefer validating directories in CI: `python -m tools.metadata_cli validate --root case_studies`
