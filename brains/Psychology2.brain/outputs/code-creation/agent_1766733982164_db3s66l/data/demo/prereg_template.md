# Demo preregistration template (IDs)

This demo prereg template intentionally contains an ID mismatch to verify that the ID checker reports a clear, actionable error.

## Canonical ID convention (summary)

- **StudyID**: `STU-YYYY-NNNN` (e.g., `STU-2025-0001`)
- **EffectID**: `<StudyID>:E<NN>` (e.g., `STU-2025-0001:E01`)

## ID fields (machine-readable)

StudyID: STU-2025-0001
EffectID: STU-2025-0002:E01

## Expected checker failure behavior (intentional)

- The checker should report a **mismatched StudyID/EffectID** because:
  - `EffectID` embeds `STU-2025-0002`, but `StudyID` is `STU-2025-0001`.
- Example of an actionable message the checker may emit:
  - "EffectID study component (STU-2025-0002) does not match StudyID (STU-2025-0001)."

## Study title

Default choice architecture tweaks and downstream behavior: a preregistered demo.

## Research questions

1. Do default options change choice rates in a forced-choice task?
2. Are effects heterogeneous by prior preference strength?

## Design overview

- Between-subjects design with two arms:
  - Control: no default pre-selected
  - Treatment: one option pre-selected as default

## Outcomes and effect definitions

Effect E01 (as referenced by EffectID above):
- Outcome: probability of choosing Option A
- Estimand: difference in proportions (treatment - control)

## Analysis plan (brief)

- Primary: difference in means (binary outcome) with 95% CI.
- Secondary: logistic regression with covariates (if available).

## Data/metadata linkage note

This template is expected to align with:
- A demo CSV and JSONL that use `StudyID = STU-2025-0001`
- The same effect defined as `EffectID = STU-2025-0001:E01`

Because this template uses `EffectID = STU-2025-0002:E01`, the checker should flag the mismatch.
