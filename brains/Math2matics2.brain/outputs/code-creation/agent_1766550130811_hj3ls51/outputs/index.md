# Outputs Manifest (Canonical)

This file is the canonical checklist of pipeline artifacts expected under `./outputs/`.
CI tests should treat this manifest as the source of truth: every path listed below must exist after a successful deterministic pipeline run.

## Expected artifacts

| Path (relative to repo root) | Type | Description |
|---|---:|---|
| `outputs/index.md` | md | This manifest (authoritative artifact list for CI). |
| `outputs/roadmap.md` | md | Pipeline roadmap / run plan (deterministic content & ordering). |
| `outputs/bibliography.bib` | bib | Bibliography in BibTeX format (stable entry ordering). |
| `outputs/coverage_matrix.csv` | csv | Coverage matrix (stable header, row ordering, and delimiter). |
| `outputs/results.json` | json | Machine-readable results with stable schema and key ordering. |
| `outputs/figure.png` | png | Deterministically generated figure (fixed seed, size, and rendering settings). |
| `outputs/test_logs.txt` | txt | Test/run logs emitted by the pipeline in a deterministic format. |

## Notes for reproducibility

- All outputs must be generated in a fully deterministic way (fixed seeds, stable sort orders, and normalized line endings).
- Filenames and relative paths listed above are normative; do not change them without updating this manifest and CI assertions.
