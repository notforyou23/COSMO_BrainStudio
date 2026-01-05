# outputs/tooling

This folder contains tooling-related output artifacts produced by the CLI, including run records, environment snapshots, and any generated helper files that make runs reproducible and auditable.

## What belongs here

Typical artifacts (file names may vary by command, but the intent stays the same):

- Run manifests: a structured record of what was executed, with inputs, outputs, parameters, and hashes.
- Environment snapshots: Python version, platform, and dependency lock/export used for the run.
- CLI invocation logs: the exact command line and resolved configuration.
- Helper exports: generated scripts/configs used to reproduce a run (when applicable).

Non-tooling artifacts (analyses, datasets, taxonomies) should live in their respective folders and be referenced from the run manifest rather than duplicated here.

## Generation by the CLI

When the CLI creates or updates artifacts, it should:

1. Create a per-run directory or per-run file set that is uniquely identifiable.
2. Write a machine-readable manifest (JSON) that links inputs -> process -> outputs.
3. Record the CLI version and a stable run identifier.
4. Capture enough environment metadata to rerun deterministically.

### Minimum manifest fields (recommended)

A run manifest should be JSON and include at least:

- run_id: stable identifier (e.g., timestamp + random suffix or UUID)
- created_utc: ISO-8601 UTC timestamp
- tool: name of CLI tool/module
- tool_version: semantic version (or commit hash)
- command: full argv string (or list)
- cwd: working directory
- inputs: list of input paths/URIs with content hashes (when file-based)
- outputs: list of output paths with content hashes
- params: resolved parameters/config used for the run
- environment: python_version, platform, and dependency snapshot reference
- warnings/errors: captured diagnostics (if any)

## Reproducibility standards

To support deterministic reruns:

- Prefer stable, explicit configuration over implicit defaults.
- Record resolved configuration (post-merge) rather than only user-supplied overrides.
- If randomness is used, record seeds and RNG libraries involved.
- If external services are called, record endpoint identifiers and request metadata when feasible (never store secrets).

### Dependency capture

At minimum, record one of:

- a lock file reference (preferred), or
- a requirements export (pip freeze), or
- an environment descriptor sufficient to rebuild the environment.

## Traceability standards

Artifacts should be traceable across cycles and runs:

- Every output file should be attributable to a run manifest.
- Use content hashing (e.g., SHA-256) for inputs/outputs when practical.
- Avoid overwriting prior artifacts; create a new run record instead.
- If an artifact must be updated in place, record a change note in the manifest and ensure it is reflected in /outputs/CHANGELOG.md.

## Naming and layout conventions

- Use lowercase folder names and kebab-case or snake_case filenames.
- Keep paths short, stable, and free of spaces.
- Prefer one run directory per invocation, e.g.:
  - outputs/tooling/runs/<run_id>/manifest.json
  - outputs/tooling/runs/<run_id>/environment.json
  - outputs/tooling/runs/<run_id>/logs.txt

## Safe writing rules (for CLI implementers)

- Write files atomically (write to temp, fsync if needed, then rename).
- Never partially update a JSON artifact; rewrite whole-file atomically.
- Ensure directories exist before writing.
- On failure, leave prior artifacts intact and write a clear error record.

## Privacy and secrets

- Do not store API keys, tokens, raw credentials, or full request bodies that may contain sensitive data.
- Redact secrets from command strings and environment dumps.
- If redaction occurs, record that redaction was applied (boolean flag) and the redaction policy name/version.
