# Build Artifact Verifier (Deterministic)

This project includes a deterministic verification step that asserts `runtime/_build` contains required, non-empty outputs. The verifier is intended to run at the end of a build/test workflow and fail fast with a clear missing/empty-file report.

## What it verifies (minimum requirements)

The verifier checks that these directories exist under `runtime/_build`, and that each contains **at least one non-empty file** with an accepted extension:

- `runtime/_build/reports` → at least one `*.json`
- `runtime/_build/tables` → at least one `*.csv`
- `runtime/_build/figures` → at least one `*.png` or `*.pdf`
- `runtime/_build/logs` → at least one `*.log` (or other configured log extensions)

“Non-empty” means file size > 0 bytes. All scans are deterministic (stable ordering) so the same directory state yields the same results and failure messages.

## Expected folder structure

A typical build output layout looks like:

runtime/_build/
  reports/
    report.json
  tables/
    table.csv
  figures/
    figure.png
  logs/
    build.log

Additional files/directories may exist; only the minimum requirements above are enforced (unless your JSON config adds more).

## How to run (single command)

Run the verifier from the repository root (or wherever the scripts/config live):

- Python:
  python scripts/verify_build_artifacts.py

If your verifier supports an explicit config flag, use:
  python scripts/verify_build_artifacts.py --config scripts/verify_build_artifacts.json

If a Makefile target is provided, use:
  make verify-artifacts

## Interpreting failures

On failure the command exits non-zero and prints a concise, deterministic report that includes:

- Which required category failed (reports/tables/figures/logs)
- Whether the directory is missing vs. present-but-empty
- Which extensions were accepted for that category
- A list of missing requirements (and, when relevant, empty files encountered)

Example failure patterns you might see:
- Missing directory: `runtime/_build/reports (directory not found)`
- No matching files: `runtime/_build/figures (no non-empty files matching: .png, .pdf)`
- Empty files only: `runtime/_build/logs (found matching files but all were empty)`

## Common causes and fixes

- Build step did not run or wrote outputs elsewhere:
  - Ensure your pipeline writes to `runtime/_build/...` paths.
- Outputs are generated but empty (0 bytes):
  - Treat this as a build failure; inspect upstream logs to determine why generation produced empty artifacts.
- Wrong extension (e.g., `.CSV` vs `.csv`):
  - The verifier may normalize case, but if not, standardize extensions or update the JSON config accordingly.
- Figures are produced as SVG only:
  - Either emit PNG/PDF in the build or extend the config to accept `.svg`.

## Configuration (JSON)

The verifier is driven by a JSON configuration file (typically `scripts/verify_build_artifacts.json`) that describes:
- Required directories relative to the project root (e.g., `runtime/_build/reports`)
- Accepted extensions for each requirement
- Minimum counts (default: at least 1 matching non-empty file per category)

If you change output locations, extensions, or add new required artifact categories, update the JSON config and keep it under version control to preserve determinism across environments.

## CI usage recommendation

Add the verifier as a final step after your build generates artifacts:
- local: run it before committing/build publishing
- CI: run it before uploading artifacts; fail the job if verification fails
