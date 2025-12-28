# Demo dataset: expected ID checker failures

This project includes a small demo dataset designed to **fail** the StudyID/EffectID integrity checker. This document explains the intentional problems and enumerates the **exact** missing/duplicate/mismatched ID errors the checker is expected to report.

## Canonical ID convention (what the checker enforces)

- **StudyID format:** `STU-YYYY-NNN`
  - `YYYY` = 4-digit year
  - `NNN` = 3-digit zero-padded study sequence within the year
  - Example: `STU-2025-001`

- **EffectID format:** `STU-YYYY-NNN:EFFF`
  - Prefix must be a valid StudyID
  - `FFF` = 3-digit zero-padded effect sequence within the study
  - Example: `STU-2025-001:E001`

- **Cross-file consistency rule (key):**
  - If an EffectID appears anywhere, its StudyID must exactly match the StudyID implied by the EffectID prefix (text before `:`).
  - The same EffectID must not be associated with different StudyIDs in different files.

## Demo files (inputs to the checker)

The checker is expected to be run on these demo inputs:

1) `data/demo/demo_effects.csv`
2) `data/demo/demo_effects.jsonl`
3) `docs/demo_prereg_template.md` (or equivalent prereg template the parser supports)

## Intentional problems in the demo dataset

The demo inputs intentionally contain:
- A **missing StudyID** in the CSV.
- A **duplicate EffectID** in the JSONL.
- A **mismatched StudyID vs EffectID prefix** in the prereg template.
- A **cross-file mismatch** where the same EffectID is mapped to different StudyIDs across files.

## Expected checker failures (exact)

### A) Missing IDs

1. **Missing StudyID (CSV)**
   - File: `data/demo/demo_effects.csv`
   - Location: row 2 (1-based row number, excluding header)
   - Problem: `StudyID` is empty/null for an effect record
   - Expected error (normalized):
     - `MISSING_STUDY_ID: data/demo/demo_effects.csv:row=2`

### B) Duplicate IDs

2. **Duplicate EffectID (JSONL)**
   - File: `data/demo/demo_effects.jsonl`
   - Locations: line 2 and line 4 (1-based line numbers)
   - Problem: the same `EffectID` appears more than once:
     - `EffectID = STU-2025-001:E002`
   - Expected error (normalized):
     - `DUPLICATE_EFFECT_ID: data/demo/demo_effects.jsonl:effect_id=STU-2025-001:E002:lines=[2,4]`

### C) Mismatched IDs (within a record)

3. **StudyID does not match EffectID prefix (prereg template)**
   - File: `docs/demo_prereg_template.md`
   - Location: the prereg entry for `EffectID = STU-2025-001:E001`
   - Problem: the prereg template declares:
     - `StudyID = STU-2025-002`
     - `EffectID = STU-2025-001:E001`
     - These conflict because the EffectID prefix implies `StudyID = STU-2025-001`.
   - Expected error (normalized):
     - `MISMATCH_STUDY_VS_EFFECT_PREFIX: docs/demo_prereg_template.md:study_id=STU-2025-002:effect_id=STU-2025-001:E001`

### D) Cross-file mismatches (same ID means different thing)

4. **EffectID maps to different StudyIDs across files**
   - IDs involved:
     - `EffectID = STU-2025-001:E001`
   - Expected observed mapping by file:
     - CSV (`data/demo/demo_effects.csv`): `StudyID = STU-2025-001`
     - JSONL (`data/demo/demo_effects.jsonl`): `StudyID = STU-2025-001`
     - Prereg (`docs/demo_prereg_template.md`): `StudyID = STU-2025-002` (intentional error)
   - Expected error (normalized):
     - `CROSSFILE_EFFECT_STUDY_MISMATCH: effect_id=STU-2025-001:E001:study_ids={STU-2025-001,STU-2025-002}:sources=[data/demo/demo_effects.csv,data/demo/demo_effects.jsonl,docs/demo_prereg_template.md]`

## Expected failure behavior

A successful run of the checker against the demo inputs must:
- Exit with a non-zero status (or return `ok=false` in its machine-readable output).
- Report **exactly the four issues above**, classified under missing / duplicate / mismatched categories.
- Provide actionable locations (file + row/line or template entry identifier) so a user can fix each issue deterministically.
