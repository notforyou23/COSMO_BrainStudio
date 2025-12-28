# /outputs Artifact Contract

This directory is the single, stable interface for all **generated artifacts** produced by the CLI tool. It is designed to be safe to write to repeatedly across cycles while remaining auditable, reproducible, and easy to diff.

## Goals
- **Predictable structure:** humans and tools can find artifacts without guessing paths.
- **Non-destructive updates:** avoid accidental overwrites; keep history via changelog + metadata.
- **Traceability:** every artifact can be tied to a run (time, inputs, tool version).
- **Diff-friendly:** prefer text formats; stable ordering; no noisy formatting.

## Directory layout (core)
- `outputs/README.md` — this contract.
- `outputs/CHANGELOG.md` — append-only, cycle-based record of structural/content changes in `/outputs`.
- `outputs/meta_analysis/` — generated analyses about analyses (quality, consistency, summaries).
- `outputs/taxonomy/` — taxonomies, schemas, category systems, mapping tables.
- `outputs/tooling/` — tooling-related artifacts (logs, reproducibility manifests, run metadata).

Each subfolder should contain its own `README.md` defining what belongs there and the minimal metadata requirements.

## Naming conventions
Prefer: `lower_snake_case` for folders; `lower_snake_case` or `kebab-case` for files.
- Use **ISO 8601 UTC** timestamps when time-scoping matters: `YYYY-MM-DDTHH-MM-SSZ` (filesystem-safe).
- If artifacts are cycle-scoped, include cycle identifier in the name or parent folder:
  - Example: `cycle_039/summary.md` or `taxonomy_v1_cycle_039.json`
- Avoid spaces; keep names short but specific.

## Preferred formats
- Text: `.md`, `.txt`
- Structured: `.json` (UTF-8, stable key ordering if possible)
- Tabular: `.csv` (UTF-8, header row)
- Avoid binary unless necessary; if binary is required, accompany with a text manifest describing it.

## Artifact rules (MUST)
1. **No silent overwrite of meaningful artifacts**
   - If writing to an existing path, do one of:
     - write a new versioned file, or
     - write atomically (temp + rename) and record the change in `CHANGELOG.md`, or
     - keep previous content by moving to an `_archive/` path within the same subfolder.
2. **Every change to `/outputs` requires a changelog entry**
   - Creating/modifying/deleting artifacts or altering structure MUST be recorded in `outputs/CHANGELOG.md`.
3. **Writes must be atomic where feasible**
   - Write to `.<name>.tmp` in the same directory, then `replace()` to final path.
4. **Include minimal provenance**
   - For non-trivial artifacts, include at least one of:
     - a sibling `*.meta.json`, or
     - a header block in the file (for Markdown/text).
   - Recommended fields: `created_at_utc`, `tool`, `tool_version`, `command`, `inputs`, `git_commit` (if available).
5. **Keep artifacts deterministic**
   - Stable ordering in JSON keys and lists where possible.
   - Avoid embedding nondeterministic content (random seeds, ephemeral IDs) unless necessary and documented.
6. **Do not write outside `/outputs`**
   - The CLI must treat `/outputs` as the only writable artifact boundary (aside from OS temp files).

## Safety guidance for CLI writers
- Ensure parent dirs exist (`mkdir(parents=True, exist_ok=True)`).
- Use atomic write:
  - write bytes/text to temp file in same directory
  - `Path(tmp).replace(final)`
- When updating a file, prefer **append-only** patterns for logs and changelogs.
- If a file is regenerated, include a version/timestamp in the filename or record the regeneration in the changelog.

## Changelog update contract (summary)
When the CLI creates or modifies anything under `/outputs`, it must immediately append to `outputs/CHANGELOG.md`:
- cycle identifier (or run identifier)
- timestamp (UTC)
- what changed (paths)
- why/how (brief)
- compatibility notes (if structure or schema changed)

## What does NOT belong in /outputs
- secrets (API keys, tokens, credentials)
- large raw datasets unless explicitly required and documented
- personal data unless approved, minimized, and protected
- transient caches that can be recreated (use OS temp or a dedicated cache outside `/outputs`)

## Backwards compatibility
Structure changes should be additive where possible. If a breaking change is unavoidable:
- record it clearly in `CHANGELOG.md`
- keep a migration note (what moved/renamed) in the relevant subfolder README
