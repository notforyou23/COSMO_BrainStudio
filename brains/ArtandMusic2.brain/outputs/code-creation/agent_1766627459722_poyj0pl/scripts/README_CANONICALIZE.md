# Canonicalize Outputs (Authoritative QA runner + Schema)

This repo may contain multiple agent/runtime output trees. Canonicalization selects **one** authoritative QA runner script and **one** authoritative schema file from existing artifacts, then copies/migrates the best-known versions into a single **canonical** `outputs/` tree and regenerates `outputs/ARTIFACT_INDEX.md` using **canonical paths only**.

## What canonicalization does
- Scans scattered agent/runtime output locations (recursively) for:
  - QA runner candidates (e.g., `scripts/qa_run*.sh`, `scripts/qa_run*.py`)
  - Schema candidates (e.g., `schemas/*.json`, `schema*.json`)
  - Output artifacts (reports, logs, validated payloads) referenced by index files or discovered by patterns
- Chooses exactly:
  - **Authoritative QA runner** (one file)
  - **Authoritative schema** (one file)
- Creates/refreshes canonical outputs:
  - `outputs/bin/` (selected runnable script(s))
  - `outputs/schemas/` (selected schema)
  - `outputs/artifacts/` (copied artifacts)
  - `outputs/ARTIFACT_INDEX.md` (canonical references only)

## Canonical directory layout
Expected canonical tree after a successful run:
- `outputs/`
  - `ARTIFACT_INDEX.md`
  - `bin/qa_runner.(sh|py)`
  - `schemas/outputs.schema.json`
  - `artifacts/` (reports/logs/json/etc.; deterministic subpaths where possible)

## CLI usage (scripts/canonicalize_outputs.py)
Run from repo root:

### Basic
- `python scripts/canonicalize_outputs.py --root . --out outputs`

### Preview only (no copy/move)
- `python scripts/canonicalize_outputs.py --root . --out outputs --dry-run`

### Restrict scan scope (faster / safer)
- `python scripts/canonicalize_outputs.py --root . --out outputs --include runtime/outputs --include outputs`

### Force a specific choice (override selection)
- `python scripts/canonicalize_outputs.py --root . --out outputs --qa-runner path/to/qa_run.sh --schema path/to/schema.json`

### Strict mode (fail if ambiguous or missing)
- `python scripts/canonicalize_outputs.py --root . --out outputs --strict`

## Selection rules (deterministic)
Canonicalization uses deterministic ordering plus scoring to pick one winner per category.

### QA runner selection (one winner)
Heuristics (typical priority order):
1. **Valid runnable file**: executable `.sh` or runnable `.py` with a shebang/entrypoint; non-empty.
2. **Naming conventions**: prefer names like `qa_run.sh`, `qa_run.py`, `qa_runner.*` over ad-hoc names.
3. **Recency**: newer `mtime` wins when otherwise comparable.
4. **Completeness**: contains expected actions/flags (e.g., runs validation, writes reports).
5. **Deterministic tiebreak**: stable lexicographic path ordering.

Output placement:
- Copied to `outputs/bin/qa_runner.(sh|py)` (or a consistent name chosen by the tool).

### Schema selection (one winner)
Heuristics (typical priority order):
1. **Valid JSON**: parses successfully.
2. **Looks like a schema**: presence of `$schema`, `type`, `properties`, `required`, etc.
3. **Recency**: newer `mtime` wins when otherwise comparable.
4. **Naming conventions**: prefer `outputs.schema.json`, `artifact.schema.json`, `schema.json`.
5. **Deterministic tiebreak**: stable lexicographic path ordering.

Output placement:
- Copied to `outputs/schemas/outputs.schema.json` (or tool-chosen canonical name).

## Index regeneration rules (ARTIFACT_INDEX.md)
- All links and paths in the regenerated index must be **canonical**, rooted under `outputs/`.
- The index must **not** reference:
  - agent-specific directories
  - `runtime/outputs/...` paths
  - ephemeral execution folders
- The index is rebuilt from canonicalized artifacts and/or discovered artifacts that were copied into `outputs/artifacts/`.

## Discovery notes (what gets scanned / ignored)
Typical scan behavior:
- Scans under `--root` plus any `--include` paths.
- Ignores common noise:
  - `.git/`, `__pycache__/`, virtualenvs, node_modules, large cache folders
- Uses deterministic traversal to ensure reproducible selection.

## Troubleshooting
### “No QA runner found”
- Ensure at least one runner exists somewhere under the scan roots (common: `scripts/qa_run.sh`).
- If the runner is named unusually, pass `--qa-runner <path>`.

### “No schema found”
- Ensure at least one schema JSON exists (common: `schemas/*.json`).
- If your schema lives elsewhere, pass `--schema <path>`.

### “Ambiguous candidates”
- Use `--strict` to surface ambiguity as an error, then override with `--qa-runner` / `--schema`.
- Use `--dry-run` to see what would be selected without copying.

### Permissions / executability
- If the selected `.sh` runner is not executable, make it executable:
  - `chmod +x outputs/bin/qa_runner.sh`
- On Windows, prefer the `.py` runner if available.

### Index still contains non-canonical paths
- Re-run canonicalization without manual edits to `outputs/ARTIFACT_INDEX.md`.
- Confirm the tool is writing the index into `outputs/` (not a runtime directory).
