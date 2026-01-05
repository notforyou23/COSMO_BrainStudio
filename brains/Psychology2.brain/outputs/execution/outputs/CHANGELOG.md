# /outputs Changelog

This file tracks **versioned, cycle-based** changes to the `/outputs` artifact set and directory structure.
Update **immediately** whenever any file/folder under `/outputs` is created, removed, renamed, or meaningfully modified.
## Changelog Rules (Contract)

- **One entry per cycle** (append newest cycle at top).
- Use a stable identifier: `Cycle <N> — v<MAJOR>.<MINOR>.<PATCH> — YYYY-MM-DD (UTC)`.
- Record only changes that affect `/outputs` artifacts, schemas, naming, or write/update behavior.
- Prefer bullet lists grouped as: **Added**, **Changed**, **Fixed**, **Removed**, **Notes**.
- If a change affects an artifact schema, include a short migration note in **Notes**.
## Cycle 1 — v0.1.0 — 2025-12-26 (UTC)

### Added
- Created `outputs/CHANGELOG.md` with a cycle-based format and update rules for `/outputs` artifacts.

### Notes
- Future cycles should document creation/modification of `/outputs/README.md` and any core folders (e.g., `meta_analysis/`, `taxonomy/`, `tooling/`) at the moment they are written.
