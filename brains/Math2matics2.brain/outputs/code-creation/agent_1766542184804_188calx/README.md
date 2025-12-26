# generated_script_1766542191957

This repository contains a small, refactored artifact-generation pipeline. It focuses on reusable utilities (filesystem/text/JSON/hashing/logging helpers) and a simple CLI that generates/export “refactor/modularize” artifacts in deterministic paths, optionally exporting the prompt text used to produce those artifacts for auditing/reproducibility.

## Layout

- `src/refactor_modularize/utils.py`  
  Reusable utility module extracted from earlier one-off scripts. Includes:
  - filesystem helpers (mkdirs, safe writes, listing)
  - text helpers (normalization, wrapping, stable joining)
  - JSON helpers (read/write with UTF-8, stable formatting)
  - hashing helpers (content hashing for deterministic IDs/paths)
  - logging helpers (consistent, minimal console output)
  - small pipeline helpers (timestamps, structured run metadata)

- `scripts/generate_artifacts.py`  
  Runnable CLI that orchestrates artifact generation/export using `utils.py`. The script is designed to be:
  - deterministic (stable output directories and filenames)
  - reproducible (optional prompt export)
  - easy to reuse in other “generate-and-export” workflows

- `docs/prompts/`  
  Prompt export artifacts captured during generation runs. These are committed/retained to make it possible to reconstruct “what was asked” when an export/refactor artifact was produced:
  - `2025-12-24T02-03-38-947Z_src_refactor_modularize_export_py_stage1_export_export_prompt.txt`
  - `2025-12-24T02-03-38-947Z_src_refactor_modularize_refactor_py_stage1_export_export_prompt.txt`

## Setup

This is a plain Python project. Create and activate a virtual environment, then install requirements (if any are present in your environment):

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -U pip
```

If you add dependencies later, prefer a minimal, pinned `requirements.txt` or `pyproject.toml` and keep `scripts/` runnable with a standard Python interpreter.

## CLI usage

Run the artifact generator as a module/script:

```bash
python scripts/generate_artifacts.py --help
```

Typical patterns (exact flags depend on the script implementation):

```bash
# Generate artifacts into deterministic output paths
python scripts/generate_artifacts.py --mode export

# Generate and also export the prompt text used for the run (for auditing)
python scripts/generate_artifacts.py --mode export --export-prompt

# Choose an explicit output directory (if supported by the CLI)
python scripts/generate_artifacts.py --mode refactor --out-dir ./out
```

### What “deterministic outputs” means here

The generator aims to make outputs stable across runs by:
- using normalized names and stable formatting (especially for JSON/text)
- hashing content or run parameters when a unique identifier is needed
- avoiding nondeterministic ordering (e.g., sorting file lists before writing)

### Prompt export (reproducibility/auditing)

When enabled, the generator writes the exact prompt text used to create/export an artifact to `docs/prompts/` with a timestamped filename. This allows you to:
- verify which instruction set produced a given artifact
- compare prompts across refactor/export branches
- reproduce the run with minimal ambiguity

## Development notes

- Keep utilities in `src/refactor_modularize/utils.py` small, pure, and well-documented.
- Keep `scripts/generate_artifacts.py` focused on orchestration (parse args → call utilities → write outputs).
- Prefer adding new helpers to `utils.py` only when they are reusable across scripts.
