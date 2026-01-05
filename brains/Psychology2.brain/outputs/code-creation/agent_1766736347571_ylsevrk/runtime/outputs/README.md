# Meta-analysis starter kit (minimal)

This folder hosts a minimal, reproducible “starter kit” for running a study-level meta-analysis end-to-end: fill a CSV extraction template, run a small analysis script, and get at least one numeric summary table written to `runtime/outputs/_build/`.

## What you will do
1) Populate a study-level extraction CSV (one row per study effect).
2) Run the analysis skeleton (a single Python entry point).
3) Review outputs in `runtime/outputs/_build/` (CSV summary tables).

## Input template (CSV)
Place your extracted data at (recommended):
- `runtime/outputs/extract_effect_sizes.csv`

Required columns (one effect per row):
- `study_id` : unique study label (string)
- `yi`       : effect estimate on an approximately normal scale (e.g., log(OR), SMD, MD) (float)
- `sei`      : standard error of `yi` (float)

Optional columns:
- `effect_type` : free-text label like `logOR`, `SMD`, `MD` (string)
- `year`, `arm`, `outcome`, `notes` : any extra columns are allowed and will be carried through.

Minimal example:
study_id,yi,sei,effect_type
StudyA,0.10,0.05,logOR
StudyB,0.00,0.10,logOR
StudyC,0.25,0.08,logOR

## Running the analysis
From the repo root (or from this folder), run the analysis entry point (created in later stages of this project) which will:
- load `runtime/outputs/extract_effect_sizes.csv` (or fall back to a small toy dataset if not present),
- compute pooled estimates (fixed effect + random effects),
- write numeric summary table(s) under `runtime/outputs/_build/`.

Recommended command:
- `python -m meta_starter.run`

Alternative (if a script is provided instead of a module entry point):
- `python runtime/outputs/run_analysis.py`

## Outputs (audit-friendly)
All generated artifacts should be written under:
- `runtime/outputs/_build/`

At minimum, expect a numeric summary table such as:
- `runtime/outputs/_build/meta_summary.csv`

Typical columns in `meta_summary.csv`:
- `model` : `fixed` or `random`
- `k`     : number of studies
- `pooled_yi` : pooled effect estimate
- `pooled_se` : standard error of pooled estimate
- `ci_low`, `ci_high` : 95% CI
- `tau2`  : between-study variance (random effects; 0 for fixed)
- `Q`, `I2` : heterogeneity stats (when available)

## Notes on computation (minimal defaults)
- Fixed effect: inverse-variance weights `wi = 1/sei^2`
- Random effects: DerSimonian–Laird tau² (DL), then `wi* = 1/(sei^2 + tau2)`
- 95% CI: normal approximation `pooled_yi ± 1.96 * pooled_se`

## Reproducibility checklist
- Keep raw extracted CSVs in `runtime/outputs/` (not in `_build/`).
- Treat `runtime/outputs/_build/` as generated outputs (safe to delete and regenerate).
- Record any preprocessing decisions in the CSV (e.g., `notes` column) and/or commit messages.
