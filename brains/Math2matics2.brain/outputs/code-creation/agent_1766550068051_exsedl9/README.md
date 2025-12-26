# Roadmap Generator

This project generates a single Markdown roadmap document containing:
- Scope boundaries (in-scope / out-of-scope)
- Subtopic list
- Prioritization policy
- Definition of Done (DoD)
- A 20-cycle milestone outline
## Repository layout

- `scripts/generate_roadmap.py`  
  Roadmap generation entrypoint (run this to produce the output file).

- `scripts/__init__.py`  
  Package marker for reliable module execution/imports.

- `outputs/roadmap_scope_success_criteria.md`  
  Default (recommended) generated roadmap output.

- `outputs/roadmap_v1.md`  
  Alternate generated output name (supported by providing a different output path).
## Requirements

- Python 3.9+ recommended
- No special system dependencies expected

If you are running in an environment where `python` points to Python 2, use `python3` instead.
## How to run

From the project root directory:

1) Generate the roadmap using the default output file:

    python scripts/generate_roadmap.py

2) Generate the roadmap to a specific path (recommended filename shown):

    python scripts/generate_roadmap.py --out outputs/roadmap_scope_success_criteria.md

3) Generate the roadmap using the alternate filename:

    python scripts/generate_roadmap.py --out outputs/roadmap_v1.md

Notes:
- The `outputs/` directory should be created automatically if it does not exist.
- Paths may be given as relative paths (from the project root) or absolute paths.
## Outputs

After a successful run, you should see one of the following files:

- `outputs/roadmap_scope_success_criteria.md` (primary)
- `outputs/roadmap_v1.md` (alternate)

The generated Markdown document includes:
- Scope boundaries (explicit in/out statements)
- Subtopic list (thematic breakdown)
- Prioritization policy (how work is ordered and tradeoffs handled)
- Definition of Done (what “complete” means for the roadmap)
- 20 cycles (milestone outline across 20 iterations)
## Re-running and overwrites

Re-running the generator will overwrite the target output file if it already exists.
If you want to keep previous versions, specify a new output filename, e.g.:

    python scripts/generate_roadmap.py --out outputs/roadmap_scope_success_criteria_v2.md
## Troubleshooting

- If you get `ModuleNotFoundError` or import issues, run from the project root so `scripts/` is discoverable.
- If the output directory is missing, ensure you have write permissions; the generator should create `outputs/` automatically.
- If `python` is not found, install Python 3 and retry with `python3`.
