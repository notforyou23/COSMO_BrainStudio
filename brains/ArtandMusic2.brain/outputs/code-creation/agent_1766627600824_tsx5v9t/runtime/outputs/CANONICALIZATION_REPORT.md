# Canonicalization Report

Generated: 2025-12-24T23:49:15Z (UTC)

## Purpose

This report documents canonicalization and migration of deliverables from agent-specific or non-canonical output locations into a single canonical tree under `runtime/outputs/`, along with any updates required to `runtime/outputs/PROJECT_TRACKER.json`.

## Status (Stage 1)

This Stage 1 deliverable initializes the canonicalization report file and defines the expected report structure. No repository scan, file migration, or tracker rewrites are performed at this stage; therefore, mappings are empty and no errors are recorded.

## Canonicalization Rules (Summary)

- Canonical root: `runtime/outputs/`
- Artifacts are migrated into canonical subfolders by type (e.g., `runtime/outputs/scripts/`, `runtime/outputs/docs/`, `runtime/outputs/data/`, `runtime/outputs/assets/`).
- Collisions should be handled deterministically (e.g., stable naming or hashing) by the canonicalizer implementation.
- `PROJECT_TRACKER.json` paths should be rewritten to canonical equivalents after migration and validated to exist.

## Old -> New Path Mappings

No mappings recorded in Stage 1.

| Action | Old Path | New Path | Notes |
|---|---|---|---|
| *(none)* |  |  |  |

## PROJECT_TRACKER.json Updates

No updates performed in Stage 1.

| Tracker Field / Pointer | Old Value | New Value | Notes |
|---|---|---|---|
| *(none)* |  |  |  |

## Skipped Items

No skipped items recorded in Stage 1.

| Reason | Path | Notes |
|---|---|---|
| *(none)* |  |  |

## Errors / Warnings

No errors recorded in Stage 1.

| Severity | Context | Message |
|---|---|---|
| *(none)* |  |  |

## Verification

No post-migration verification performed in Stage 1 (no migration executed).

## Notes

- This file is intended to be appended/overwritten by the canonicalization script once discovery, migration, and tracker update steps run.
- When canonicalization is executed, this report should include:
  - A complete old->new mapping table for every migrated/copied artifact.
  - A list of skipped items with clear reasons.
  - Any errors encountered, including missing sources, permission issues, or tracker rewrite failures.
  - A verification summary confirming referenced artifacts exist in canonical locations.
