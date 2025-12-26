# Artifact Index (Canonical)

This file enumerates required project deliverables and their **canonical** locations under `/outputs`. If legacy locations exist, they are recorded with migration status.

## Legend

- **Canonical path**: The single source of truth under `/outputs/...`
- **Legacy path**: Any historical/non-canonical location (e.g., `runtime/outputs/...`)
- **Migration status**:
  - **migrated**: present at canonical path (legacy may remain)
  - **not_migrated**: only found in legacy path(s)
  - **unknown**: not verified by this index alone
## Required deliverables

| Deliverable | Category | Canonical path | Legacy path(s) | Migration status |
|---|---|---|---|---|
| ARTIFACT_INDEX.md | documentation | /outputs/ARTIFACT_INDEX.md | (none) | migrated |
| artifact_discoverability_fix.py | script | /scripts/artifact_discoverability_fix.py | (optional) runtime/outputs/.../scripts/artifact_discoverability_fix.py | unknown |
| required_deliverables.json | support | /support/required_deliverables.json | (optional) runtime/outputs/.../support/required_deliverables.json | unknown |
| ARTIFACT_INDEX_AND_TRACKER_MAINTENANCE.md | documentation | /docs/ARTIFACT_INDEX_AND_TRACKER_MAINTENANCE.md | (optional) runtime/outputs/.../docs/ARTIFACT_INDEX_AND_TRACKER_MAINTENANCE.md | unknown |
## Notes

- This index is intended to be generated/maintained by the discoverability script and should reflect the canonical `/outputs` layout even if legacy copies exist.
- Tracker files (e.g., `PROJECT_TRACKER.json`) should reference **only** canonical paths once canonicalization/migration has been performed.
