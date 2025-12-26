# Minimal runnable computational skeleton

This folder documents how to run `generate_artifacts.py` to deterministically create example artifacts in `outputs/` (a PNG plot, a results JSON, and run metadata).

## Quickstart

### 1) Create and activate a virtual environment (recommended)

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows (PowerShell)
# .venv\Scripts\Activate.ps1
```

### 2) Install pinned dependencies

From the repo root (or anywhere), run:

```bash
pip install -r outputs/src/requirements.txt
```

### 3) Run the generator

```bash
python outputs/src/generate_artifacts.py
```

On success, the script writes deterministic artifacts under `outputs/` (relative to the repo root).

## Outputs

Expected files (names may include a timestamped subfolder depending on implementation):

- `outputs/results.json` (or `outputs/**/results.json`): summary statistics and configuration
- `outputs/plot.png` (or `outputs/**/plot.png`): plot of the synthetic data
- `outputs/run_metadata.json` (or `outputs/**/run_metadata.json`): environment + run info

## Determinism / reproducibility

The artifact generator is intended to be deterministic:
- it uses a fixed random seed for synthetic data generation
- it avoids nondeterministic system-state inputs (unless explicitly recorded in run metadata)
- results should match across runs given the same Python version and dependency versions in `requirements.txt`

## Notes

- Run the script from the repo root to keep output paths simple.
- If you see import errors, confirm you installed dependencies into the same environment you are using to run Python:

```bash
python -c "import sys; print(sys.executable)"
pip -V
```
