# /outputs/tools

This folder stores **tool-generated artifacts** (outputs from scripts/CLIs/notebooks) along with enough **run metadata** to reproduce and audit how each artifact was produced.

Use this folder for:
- Data extraction outputs (e.g., scraped tables, parsed PDFs, converted formats)
- Intermediate transforms (e.g., normalized CSV/JSON, merged datasets)
- Diagnostics (e.g., validation reports, profiling summaries)
- Figures and tables produced by code
- Any “derived” artifact created by a tool run

Do **not** store:
- Source code (keep in the repository)
- Human-written narrative drafts (use appropriate docs folders)
- Raw primary sources unless they are *fetched by a tool* and must be tracked as an output
## Layout and naming conventions

Prefer this structure:

outputs/tools/
  <tool_name>/
    <YYYY-MM-DD>_<run_name>__v<semver_or_int>/
      manifest.json
      stdout.txt
      stderr.txt
      outputs/...
      inputs_snapshot/...

Example:
outputs/tools/pdf_extract/
  2025-12-26_trial_registry_parse__v1/
    manifest.json
    stdout.txt
    outputs/records.jsonl

Guidelines:
- `<tool_name>`: short, stable identifier (snake_case), e.g., `pdf_extract`, `citation_parse`, `stats_report`
- `<run_name>`: descriptive but short; avoid spaces; e.g., `cochrane_2020_search`, `pilot_parse`
- Versioning:
  - Use `__v1`, `__v2` for iterative runs.
  - Use semver `__v0.1.0` if the tool is evolving and changes are meaningful.
## Required traceability: `manifest.json`

Every run folder SHOULD include a `manifest.json` capturing:

Minimum fields (recommended):
- `schema_version`: e.g., "1.0"
- `tool`: name + version (and commit if available)
- `run_id`: unique identifier (timestamp + short random or hash)
- `timestamp_utc`: ISO 8601 UTC time
- `command`: full command invoked (or notebook cell command)
- `cwd`: working directory
- `parameters`: parsed flags/params (JSON object)
- `inputs`: list of input paths/URIs with hashes (when feasible)
- `outputs`: list of produced files with relative paths + hashes
- `environment`:
  - python version
  - OS info
  - key packages + versions
  - optional container image / conda env name
- `randomness`:
  - random seeds used
  - determinism notes (e.g., multithreading, nondeterministic ops)
- `notes`: free-text (why the run exists, known issues)

Hashing:
- Prefer SHA-256 for files when practical.
- If hashing is too expensive (very large files), record size + mtime and explain in `notes`.
## Capturing stdout/stderr and logs

Include one or more of:
- `stdout.txt` and `stderr.txt` (captured console output)
- `run.log` (structured logs)
- `report.json` / `report.md` (validation summary)

If a tool produces multiple logs, name them clearly:
- `validation_report.json`
- `profiling.txt`
- `warnings.txt`
## Recording parameters and run metadata (quick checklist)

For each tool run, ensure the run folder contains:
- A stable run folder name (see naming conventions)
- `manifest.json` with command + parameters
- Captured console output (stdout/stderr) or log file
- Output files under `outputs/` (recommended)
- If inputs are local files, either:
  - reference them with paths + hashes in the manifest, or
  - copy minimal `inputs_snapshot/` (only if legally/ethically appropriate)

Avoid ambiguity:
- Do not overwrite prior runs; create a new versioned run folder.
- If a run is superseded, keep it and add a note in the new manifest referencing the prior run.
## Example `manifest.json` (minimal)

{
  "schema_version": "1.0",
  "tool": {"name": "pdf_extract", "version": "0.3.2", "git_commit": "abc1234"},
  "run_id": "2025-12-26T05:30:12Z_7f3c1a",
  "timestamp_utc": "2025-12-26T05:30:12Z",
  "command": "python -m tools.pdf_extract --in inputs/papers --out outputs/tools/pdf_extract/2025-12-26_run__v1/outputs",
  "cwd": "/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution",
  "parameters": {"in": "inputs/papers", "out": "outputs/.../outputs"},
  "inputs": [{"path": "inputs/papers/p1.pdf", "sha256": "..." }],
  "outputs": [{"path": "outputs/records.jsonl", "sha256": "...", "bytes": 123456}],
  "environment": {"python": "3.11.6", "platform": "macOS-14.5", "packages": {"pandas": "2.2.3"}},
  "randomness": {"seed": 0, "notes": "single-threaded"},
  "notes": "Extracted tables from pilot set; see stderr for 2 parse warnings."
}

You may extend this schema as needed, but keep it JSON and machine-readable.
## Reproducibility expectations

A reviewer should be able to:
1) Identify which tool produced an artifact.
2) Re-run the tool with the recorded command/parameters.
3) Verify outputs via recorded hashes (or documented alternatives).

If perfect reproducibility is not possible (e.g., API calls, web scraping), document:
- request URLs/endpoints
- authentication method (never store secrets)
- response caching strategy
- timestamps and rate limits
- any non-deterministic behavior
