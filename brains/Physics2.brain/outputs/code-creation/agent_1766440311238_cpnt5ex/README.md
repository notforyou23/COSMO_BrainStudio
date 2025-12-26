# generated_script_1766440325922

Prototype numerical/symbolic experiments with a small CLI that runs preconfigured demos and writes reproducible artifacts (tables/figures) to disk.

## What this project does

- Runs **numerical** and **symbolic** toy experiments from the command line.
- Writes results into a timestamped (or user-chosen) output directory.
- Prints a concise stdout summary so runs can be compared or copied into reports.

The repository is intentionally minimal: a single entry point (`src/main.py`) selects an experiment, executes it, saves artifacts, and reports what was produced.

## Quickstart

### 1) Create an environment and install

Using `pip` (works with venv/conda):

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

pip install -r requirements.txt
# or, if using pyproject:
pip install -e .
```

### 2) Run an experiment

```bash
python -m src.main --help
python -m src.main --experiment <name> --outdir outputs/run1
```

Typical behavior:
- `--experiment` chooses a configured demo (e.g., convergence test, symbolic identity check).
- `--outdir` is created if needed; all artifacts go inside it.
- stdout ends with a short summary: selected experiment, key parameters, and filenames written.

## Common CLI options (expected)

While exact flags are defined in `src/main.py`, the CLI is designed around:

- `--experiment NAME` : which experiment to run
- `--outdir PATH` : where to place artifacts (tables/figures/metadata)
- `--seed INT` : deterministic randomness when applicable
- `--no-plot` : skip figure generation (still writes tables/JSON)

Run `python -m src.main --help` to confirm available options in your version.

## Outputs and reproducibility

A run should produce (at minimum):

- One machine-readable result file (e.g., `results.json` or `metrics.csv`)
- Optional figures (e.g., `figure_*.png`)
- A small metadata record capturing parameters (experiment name, versions, seed)

Recommended workflow:

```bash
python -m src.main --experiment demo --seed 0 --outdir outputs/demo_seed0
python -m src.main --experiment demo --seed 1 --outdir outputs/demo_seed1
diff -r outputs/demo_seed0 outputs/demo_seed1 || true
```

## Project layout

- `src/main.py` : CLI entry point; experiment registry + runner; writes artifacts
- `examples/expected_outputs.md` : copy/paste commands and what they should print/write
- `requirements.txt` / `pyproject.toml` : dependencies and packaging metadata
- `outputs/` : (user-created) generated artifacts from runs

## Notes

- This project targets Python 3.10+.
- If plotting is enabled, ensure your environment can write image files; headless environments should still work with non-interactive backends.

## Troubleshooting

- If `--help` fails, confirm you’re invoking the module correctly: `python -m src.main`.
- If import errors occur, install dependencies (`pip install -r requirements.txt`) or install editable (`pip install -e .`) when using `pyproject.toml`.
