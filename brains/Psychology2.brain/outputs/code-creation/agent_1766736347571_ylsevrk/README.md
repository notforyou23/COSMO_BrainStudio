# generated_script_1766735535722 — ID Convention + CSV/JSONL Mismatch Checker

This project defines a single canonical ID convention shared across CSV and JSONL inputs and provides a CLI tool that validates IDs and reports cross-file mismatches with actionable errors and non-zero exit codes.

## Canonical ID convention (used identically in CSV and JSONL)

All IDs are **case-sensitive** and must match these formats:

- `study_id`: `STUDY-` + 6 digits  
  - Regex: `^STUDY-\d{6}$`  
  - Example: `STUDY-000123`

- `effect_id`: `EFFECT-` + 8 digits  
  - Regex: `^EFFECT-\d{8}$`  
  - Example: `EFFECT-00001234`

The same `study_id`/`effect_id` strings must appear in **both** files for the same effect record.

Source of truth: `src/id_convention.py` (constants + validation helpers).
## Input schemas

### CSV: `effects.csv`

Required columns (header names must match exactly):

- `study_id` (string, must match the `study_id` regex)
- `effect_id` (string, must match the `effect_id` regex)

Notes:
- Extra columns are allowed and ignored by the mismatch checker.
- Duplicate (`study_id`, `effect_id`) rows are treated as an error.

### JSONL: `effects.jsonl`

File must be newline-delimited JSON where each line is an object with:

- `study_id` (string, must match the `study_id` regex)
- `effect_id` (string, must match the `effect_id` regex)

Notes:
- Extra keys are allowed and ignored by the mismatch checker.
- Duplicate (`study_id`, `effect_id`) records are treated as an error.
- Invalid JSON lines are reported with line number.
## What the mismatch checker verifies

`src/mismatch_checker.py` performs:

1. **Schema checks**
   - CSV has required columns.
   - JSONL parses and has required keys.

2. **ID validation**
   - Every `study_id` and `effect_id` matches the canonical regex.

3. **Uniqueness**
   - No duplicate (`study_id`, `effect_id`) pairs within a file.

4. **Cross-file matching**
   - Every pair in CSV exists in JSONL (no “missing in JSONL”).
   - Every pair in JSONL exists in CSV (no “missing in CSV”).

On any failure it prints clear errors to stderr and exits non-zero.
## Demo fixtures

- Passing fixtures:
  - `fixtures/passing/effects.csv`
  - `fixtures/passing/effects.jsonl`

- Failing fixtures (intentional):
  - `fixtures/failing/effects.csv`
  - `fixtures/failing/effects.jsonl`

The failing set is designed to trigger multiple errors (format violations and/or cross-file mismatches) so you can see the checker’s messages.
## Example commands

Run from the repository root.

### 1) Passing run (expected exit code: 0)

python -m src.mismatch_checker \
  --csv fixtures/passing/effects.csv \
  --jsonl fixtures/passing/effects.jsonl

Expected output (example):

OK: 0 errors. CSV and JSONL pairs match (N pairs).

### 2) Failing run (expected exit code: non-zero)

python -m src.mismatch_checker \
  --csv fixtures/failing/effects.csv \
  --jsonl fixtures/failing/effects.jsonl

Expected errors include messages like (exact wording may differ):

ERROR: Invalid study_id at CSV row 2: 'study-001234' (expected ^STUDY-\d{6}$)
ERROR: Invalid effect_id at JSONL line 3: 'EFFECT-12' (expected ^EFFECT-\d{8}$)
ERROR: Pair missing in JSONL: (study_id=STUDY-000101, effect_id=EFFECT-00000001)
ERROR: Pair missing in CSV: (study_id=STUDY-000102, effect_id=EFFECT-00000002)

The process should exit with a non-zero code when any ERROR is present.
