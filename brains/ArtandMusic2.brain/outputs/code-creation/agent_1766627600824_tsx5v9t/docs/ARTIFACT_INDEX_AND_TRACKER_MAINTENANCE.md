# ARTIFACT_INDEX + Tracker Maintenance

This document describes how to run the artifact discoverability maintenance script, how required deliverables are defined, and how tracker path canonicalization works and is verified.

## What the system does

The maintenance workflow is designed to keep three things consistent:

1) **Definition of deliverables**: a declarative list of “required deliverables” (artifacts that must exist and be discoverable).
2) **Artifact index**: `outputs/ARTIFACT_INDEX.md` generated from that list, showing canonical paths and any legacy locations plus migration status.
3) **Tracker canonicalization**: `PROJECT_TRACKER.json` (or similar tracker JSON) updated so references point to **canonical** `/outputs/...` paths only.

The workflow does *not* invent deliverables; it only enforces consistency between the declarative list, the index, and the tracker JSON.
## Files and roles

- `support/required_deliverables.json`
  - Source of truth for which deliverables must exist.
  - Each entry includes the canonical `/outputs/...` path and may include one or more legacy locations used by earlier runtime layouts.

- `scripts/artifact_discoverability_fix.py`
  - Single runnable script.
  - Discovers/validates deliverables, generates `outputs/ARTIFACT_INDEX.md`, and updates the tracker JSON to use canonical paths.

- `outputs/ARTIFACT_INDEX.md`
  - Generated/maintained output index.
  - Lists each required deliverable with:
    - canonical path under `/outputs`
    - legacy path(s) (if any)
    - migration status (see below)

- Tracker JSON (example: `PROJECT_TRACKER.json`)
  - Human-/agent-maintained project state.
  - After canonicalization, it should only contain canonical `/outputs/...` paths for artifacts.

## Deliverables definition (required_deliverables.json)

The required deliverables file is a declarative list. Each deliverable should minimally define:

- **id**: stable identifier used in reporting (string).
- **canonical_path**: the required location under `/outputs/...` (string).
- **category/description/metadata**: optional fields for readability and reporting.
- **legacy_paths**: optional list of older locations (strings). These may include prior layouts like `runtime/outputs/...` or other historical paths.

A deliverable is considered discoverable if its canonical path exists. Legacy paths are used to determine whether the artifact exists elsewhere and whether it has been migrated.
## Migration status logic

The script assigns a migration status per deliverable based on filesystem presence:

- **migrated**: canonical exists (regardless of legacy existence).
- **legacy_only**: canonical missing but one or more legacy paths exist.
- **missing**: neither canonical nor legacy paths exist.
- **conflict** (optional policy): canonical exists and legacy exists but contents differ (only possible if the script performs hashing/size checks). If the script does not compare contents, it should still surface “both present” for operator review.

The index should make it easy to answer:
- “Is the required artifact present at its canonical location?”
- “If not, does it still exist in a legacy location?”
- “Do we need to migrate/copy it, or regenerate it?”

## Running the script

Run from the repository/workspace root (so relative paths resolve consistently):

- `python scripts/artifact_discoverability_fix.py`

Common options (if implemented by the script) may include:
- `--required support/required_deliverables.json`
- `--index outputs/ARTIFACT_INDEX.md`
- `--tracker PROJECT_TRACKER.json`
- `--dry-run` (no writes; print planned changes)

Expected outputs:
- `outputs/ARTIFACT_INDEX.md` is created/updated.
- The tracker JSON is rewritten so artifact references use canonical `/outputs/...` paths.

## Tracker canonicalization: how it works

Canonicalization updates any tracker field that looks like a path reference to an artifact so that:

- Any legacy path is replaced with the matching canonical `/outputs/...` path.
- Any relative path is normalized to the canonical path form.
- If the tracker references an artifact that is not in `required_deliverables.json`, the script should either:
  - leave it unchanged (conservative), or
  - normalize it only if it clearly maps to a known canonical deliverable.

Path matching is typically done by:
- exact match against known `legacy_paths`
- exact match against canonical paths
- optionally, normalized comparisons (e.g., stripping leading `./`)

The script should avoid “guessing” mappings that could corrupt the tracker.

## Verification: how correctness is checked

After a run, verify the following:

1) **Index completeness**: every deliverable in `support/required_deliverables.json` appears in `outputs/ARTIFACT_INDEX.md`.
2) **Canonical preference**: for each deliverable, the canonical `/outputs/...` path is displayed and used as the primary location.
3) **Tracker canonical-only invariant**:
   - Search the tracker JSON for legacy path fragments (e.g., `runtime/outputs`, `./runtime/outputs`, or any legacy prefixes used historically).
   - Confirm that artifact references are expressed only as `/outputs/...` canonical paths (or repository-relative `outputs/...`, depending on project convention—use exactly one convention and enforce it).
4) **No unexpected edits**: diff the tracker JSON; only path fields should change, not unrelated metadata.

If any deliverable is `legacy_only`, the correct remediation is either:
- migrate/copy the artifact to its canonical `/outputs/...` location, or
- regenerate the artifact via its producing pipeline, then rerun the script to confirm status becomes `migrated`.

## Operational guidance

- Treat `support/required_deliverables.json` as the contract: update it when a deliverable is added/removed/renamed.
- Prefer changing producer pipelines to write directly to canonical `/outputs/...` paths.
- Rerun the script after any significant pipeline run that creates/updates outputs to keep the index and tracker consistent.
