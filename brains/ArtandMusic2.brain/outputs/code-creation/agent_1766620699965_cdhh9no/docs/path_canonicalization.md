# Path canonicalization (runtime/outputs → outputs)

This project treats `outputs/` as the **canonical artifact tree**. Some generators historically wrote into `runtime/outputs/`; the canonicalization step migrates those artifacts into `outputs/`, detects duplicates, and (optionally) rewrites in-repo references so that developers and CI consistently point at the canonical paths.
## Command

The CLI exposes a canonicalization command (name may vary by entrypoint):

- `cosmo path-canonicalize`
- or `python -m src.cli path-canonicalize` (depending on how your CLI is wired)

Run it from the repo root.
## What it does (high level)

1. Scan `runtime/outputs/` for artifacts.
2. For each artifact, compute its canonical destination under `outputs/` preserving relative structure.
3. Sync/copy into `outputs/` with **duplicate detection**:
   - If destination does not exist: copy.
   - If destination exists and content is identical: mark as duplicate (no change).
   - If destination exists and content differs: mark as conflict; do not overwrite unless explicitly allowed.
4. Optionally rewrite textual references in-repo from `runtime/outputs/...` → `outputs/...`.
5. Emit a report at `outputs/qa/path_canonicalization_report.md` describing actions, duplicates, conflicts, and reference rewrites.
## Key options

Exact flags may differ slightly; the implementation supports the following concepts:

- `--runtime-root runtime/outputs`  
  Source tree to migrate from.

- `--outputs-root outputs`  
  Canonical destination tree.

- `--report-path outputs/qa/path_canonicalization_report.md`  
  Where to write the markdown report (created if missing).

- `--dry-run`  
  Perform discovery and decision-making without writing files or rewriting references.

- `--rewrite-references`  
  Rewrite in-repo references (e.g., `.md`, `.py`, `.yaml`, `.json`) that point to `runtime/outputs/` so they point to `outputs/`.

- `--rewrite-glob "**/*.{md,py,yaml,yml,json,toml,txt}"`  
  Control which files are eligible for rewriting. Binary files are never rewritten.

- `--include-glob / --exclude-glob`  
  Narrow or skip migration targets (useful to avoid large caches or transient files).

- `--on-conflict {skip,fail}` (default: `fail`)  
  If destination exists with different content, either stop with a non-zero exit (`fail`) or record and skip (`skip`).

- `--delete-runtime` (dangerous)  
  After successful sync, remove migrated files from `runtime/outputs/`. Prefer leaving sources intact until CI is stable.
## Safety guarantees

The command is designed to be safe by default:

- **No destructive actions by default**: sources under `runtime/outputs/` are not deleted unless `--delete-runtime` is set.
- **No silent overwrites**: if a destination exists with different content, the default behavior is to fail (or record-and-skip if configured).
- **Content-based duplicate detection**: identity is determined by hashing file content, not timestamps.
- **Report is always written** (unless the process is terminated): it is intended to be the source of truth for what happened.
- **Deterministic mapping**: the destination path is computed from the relative path under `runtime/outputs/` into `outputs/`.
## Canonical path mapping

Given a file:
- `runtime/outputs/<REL_PATH>`

The canonical location is:
- `outputs/<REL_PATH>`

Examples:
- `runtime/outputs/reports/run_001/summary.md` → `outputs/reports/run_001/summary.md`
- `runtime/outputs/schemas/foo.schema.json` → `outputs/schemas/foo.schema.json`
- `runtime/outputs/tools/cli_tool.py` → `outputs/tools/cli_tool.py`
## Report contents (outputs/qa/path_canonicalization_report.md)

The report is markdown intended for humans and CI logs. Expect sections like:

- **Run metadata**: timestamp, runtime root, outputs root, command flags.
- **Summary**: counts of scanned files, copied files, duplicates, conflicts, rewritten references, skipped files.
- **Moved/synced artifacts**: source → destination, size, hash.
- **Duplicates (identical)**: files that already existed in `outputs/` with identical content.
- **Conflicts (different content)**: paths where destination existed with different content, and what action was taken.
- **Reference rewrite log** (if enabled): files rewritten, number of replacements, and examples of rewritten paths.
- **Notes for follow-up**: common causes of conflicts (e.g., divergent generation settings) and recommended remediation.
## Developer workflow

Recommended local workflow when adopting canonical outputs:

1. Generate artifacts as usual (even if they land in `runtime/outputs/`).
2. Run canonicalization:
   - `cosmo path-canonicalize --rewrite-references`
3. Commit any in-repo reference changes and any canonical artifacts you intentionally version (if applicable).
4. Prefer updating generators to write directly into `outputs/` over time; canonicalization remains as a safety net.
## CI guidance

- Add a CI job step after artifact generation:
  - `cosmo path-canonicalize --on-conflict fail`
- Keep `--dry-run` available for fast validation steps where you only need the report.
- Use the report as a CI artifact; it should make it obvious when duplication persists or when conflicts occur.
- When enabling `--rewrite-references` in CI, ensure the working tree is clean or the step runs in a context where modifications are expected.
## Troubleshooting

- **Conflicts reported**: two different versions of the same artifact exist. Prefer regenerating into a clean workspace, or delete the incorrect destination artifact and rerun canonicalization.
- **Duplicates remain**: duplicates are normal during transition; the command records them. Consider `--delete-runtime` only once you trust the canonical paths.
- **Rewrites missed**: ensure the target file types are included by the rewrite glob(s) and that the files are text (binary files are ignored).
