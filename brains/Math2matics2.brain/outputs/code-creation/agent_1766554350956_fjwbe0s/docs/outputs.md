# Canonical `outputs/` directory

This repo standardizes all generated artifacts under a single, repo-relative `./outputs/` directory at the repository root. The goal is to prevent “lost” artifacts spread across agent- or tool-specific folders and to provide a stable place for humans and automation to find results.

Two files are always produced alongside consolidated artifacts:
- `outputs/index.md`: human-readable inventory (with links) of consolidated artifacts.
- `outputs/manifest.json`: machine-readable inventory including SHA-256 hashes for integrity checks and caching.

> Note: This document describes the intended structure and behavior of the consolidation tooling. The consolidator does **not** write outside repo-relative paths.
## Canonical structure

The consolidator creates/updates:
- `./outputs/` (canonical root for artifacts)
- `./outputs/index.md` (generated)
- `./outputs/manifest.json` (generated)

Recommended sub-structure (the consolidator may create these as needed):
- `outputs/artifacts/` – promoted “best” artifacts (reports, charts, exports, models, etc.)
- `outputs/runs/<run_id>/` – optional run-scoped copies or grouped outputs when multiple runs must coexist
- `outputs/logs/` – optional consolidation logs (if enabled by the script)

The exact set of folders can evolve; the contract is that **all consolidated artifacts are discoverable from `outputs/index.md` and `outputs/manifest.json`.**
## What gets consolidated (discovery)

The consolidation process scans “agent-specific” and tool-specific output paths (e.g., per-agent folders, per-run folders, tool default output folders) and discovers candidate artifacts.

Typical candidates include:
- Documents: `.md`, `.pdf`, `.html`, `.txt`
- Data: `.json`, `.csv`, `.parquet`, `.yaml`, `.yml`
- Media: `.png`, `.jpg`, `.svg`
- Notebooks: `.ipynb`
- Archives: `.zip` (used sparingly; see Selection)

Discovery is file-based. Directories are not treated as artifacts unless explicitly packaged (e.g., `.zip`).
## How “best” artifacts are selected (selection + promotion)

When multiple candidates represent the same “logical artifact,” the consolidator promotes only the best one into `./outputs/` to avoid duplication and ambiguity.

Selection heuristics (typical; exact behavior is defined by the consolidator implementation):
1. Prefer artifacts that look “final” over “intermediate”
   - Names containing `final`, `report`, `summary`, `export` are preferred
   - Names containing `tmp`, `draft`, `partial`, `debug`, `checkpoint` are de-prioritized
2. Prefer richer formats when content overlaps
   - `pdf/html` may outrank `txt`; `parquet` may outrank `csv` (configurable)
3. Prefer newest stable artifacts
   - More recent modification time can break ties
4. Prefer non-empty, readable files
   - Zero-byte outputs are ignored
5. Avoid duplicates by content hash
   - If two files have identical SHA-256, only one is promoted

Promotion behavior:
- Artifacts are copied (not moved) into `./outputs/` so original tool/agent folders remain intact.
- Name collisions are resolved deterministically (e.g., by suffixing a short hash or by scoping into `runs/<run_id>/`).
## Generated inventories

### `outputs/manifest.json`
A machine-readable list of consolidated files containing, at minimum:
- `path` (repo-relative, under `outputs/`)
- `sha256`
- `bytes`
- `modified` (timestamp; optional)
- `source` (original discovered path; optional but recommended)

This file is suitable for:
- CI artifact publishing
- caching / incremental rebuilds
- integrity checking
- downstream automation that needs stable references

### `outputs/index.md`
A human-readable listing of outputs, typically grouped by type or run. It should include:
- artifact name and relative path
- size and/or date (optional)
- SHA-256 (optional, or link to manifest)
## Running the consolidation script

The repository includes a CLI consolidator:
- `scripts/consolidate_outputs.py`

Typical usage:
- Run from repo root:
  - `python scripts/consolidate_outputs.py`
- With explicit inputs (example flags; see `--help` for your repo’s exact interface):
  - `python scripts/consolidate_outputs.py --scan ./agents --scan ./tool_outputs --out ./outputs`
- To regenerate inventories without copying:
  - `python scripts/consolidate_outputs.py --index-only`

Expected behavior:
- Ensures `./outputs/` exists
- Copies/promotes selected artifacts into `./outputs/`
- Rewrites `./outputs/index.md` and `./outputs/manifest.json` each run
## Guidance for contributors

If you write code that produces artifacts:
- Prefer writing to a run-scoped folder and/or a tool-specific folder, then rely on consolidation for the canonical view.
- Avoid hardcoding absolute paths; use repo-relative paths.
- Make artifact filenames descriptive and stable (include dataset/model name and date or run id).
- If your output is “intermediate,” label it clearly (e.g., `*_debug.json`, `*_draft.md`) so selection heuristics can prefer the final result.

If you consume artifacts:
- Read from `./outputs/manifest.json` for automation.
- Use `./outputs/index.md` for manual browsing.

This standardization makes outputs predictable, reviewable, and easy to publish in CI or share externally.
