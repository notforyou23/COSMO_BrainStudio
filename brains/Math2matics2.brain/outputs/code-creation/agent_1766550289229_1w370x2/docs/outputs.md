# Unified outputs directory

This project uses a single, consistent outputs directory resolver for **all** artifacts written by pipelines, experiments, and tests.

The resolver lives in `src/outputs.py` and is the only supported way to decide where to write files.

## OUTPUT_DIR resolver

`src/outputs.py` defines:

- `OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./outputs")).resolve()`

Behavior:

- Default: `./outputs` (resolved to an absolute path).
- Override: set the `OUTPUT_DIR` environment variable to any path (relative or absolute); it will be resolved to an absolute path at runtime.
- All downstream code should write artifacts under `OUTPUT_DIR` (never hardcode `./outputs`, `./artifacts`, `/tmp`, etc.).

## Helper functions

`src/outputs.py` also provides small helpers intended for widespread use:

- `ensure_dir(path: Path) -> Path`  
  Creates the directory (parents included) if needed and returns the directory `Path`.

- `write_text(path: Path, text: str, *, encoding="utf-8") -> Path`  
  Ensures `path.parent` exists, writes text, and returns the file `Path`.

- `write_json(path: Path, obj: Any, *, indent=2, sort_keys=True) -> Path`  
  Ensures `path.parent` exists, writes JSON, and returns the file `Path`.

These helpers keep artifact writing consistent and remove repeated boilerplate.

## Recommended usage patterns

### Pipelines

- Treat `OUTPUT_DIR` as the root folder for all pipeline artifacts.
- Create a subfolder per pipeline run, stage, or dataset to avoid collisions.

Example:

- `OUTPUT_DIR / "pipelines" / "<pipeline_name>" / "<run_id>" / ...`

### Experiments

- Use a stable experiment name plus a unique run identifier (timestamp, hash, or UUID).
- Keep raw inputs, configs, metrics, and plots together under the run directory.

Example:

- `OUTPUT_DIR / "experiments" / "<exp_name>" / "<run_id>" / "metrics.json"`

### Tests

- Tests should not write into the repository tree directly.
- Prefer an isolated outputs root by setting `OUTPUT_DIR` during tests (CI and local).
- If a test needs to write files, it should do so under `OUTPUT_DIR / "tests" / <test_name>`.

This makes tests deterministic and avoids polluting developer workspaces.

## Environment variable examples

### Local (macOS/Linux)

- One command:
  - `OUTPUT_DIR=./outputs_local python -m your_module`

- Session:
  - `export OUTPUT_DIR=/abs/path/to/outputs`
  - `pytest`

### CI

CI should set `OUTPUT_DIR` to a workspace-local directory to keep artifacts contained and easy to collect.

## Conventions

- Do not scatter output roots (e.g., `runs/`, `results/`, `artifacts/`) across the codebase.
- Do not assume the current working directory; always build paths from `OUTPUT_DIR`.
- Prefer structured subdirectories and stable filenames:
  - `config.json`, `metrics.json`, `stdout.txt`, `predictions.jsonl`, etc.

## What to change when adding new outputs

When adding a new artifact write:

1. Import from `src.outputs`:
   - `from src.outputs import OUTPUT_DIR, ensure_dir, write_text, write_json`
2. Build the destination path under `OUTPUT_DIR`.
3. Use `ensure_dir` / `write_text` / `write_json` to create directories and write files.
