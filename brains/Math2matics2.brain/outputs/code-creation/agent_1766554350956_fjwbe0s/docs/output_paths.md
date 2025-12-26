# Output path policy

This repository standardizes where generated artifacts are written (plots, model outputs, reports, caches, temporary build products, etc.). All code must resolve output locations through a single helper (`src/output_paths.py`) and must not write to absolute `/outputs` paths.

## Goals

- Make output locations consistent across local runs and CI.
- Keep the project runnable without special filesystem permissions.
- Allow a single override point for output location.
- Prevent accidental writes to absolute `/outputs` (often unwritable in CI/containers).

## Policy (authoritative)

1. **Default output directory**: `./outputs` (relative to the current working directory).
2. **Override**: set environment variable `OUTPUT_DIR` to a directory path.
3. **Only one resolver**: all code and tests must use the helper in `src/output_paths.py` to:
   - resolve the output directory,
   - create directories as needed,
   - build child output paths.
4. **Forbidden**: attempting to write to absolute `/outputs` (e.g., `/outputs/foo.txt`) is rejected.

## Environment variable: `OUTPUT_DIR`

- If `OUTPUT_DIR` is set, the helper uses it as the base output directory.
- If `OUTPUT_DIR` is not set or is empty, the helper falls back to `./outputs`.
- `OUTPUT_DIR` may be relative or absolute (except the specific forbidden `/outputs` root case).
- The helper is responsible for creating the directory (and parents) when needed.

Examples:

- macOS/Linux (bash/zsh):
  - `export OUTPUT_DIR=./outputs`
  - `export OUTPUT_DIR=/tmp/my-run-outputs`
- Windows (PowerShell):
  - `$env:OUTPUT_DIR = ".\outputs"`
  - `$env:OUTPUT_DIR = "C:\temp\my-run-outputs"`

## Usage pattern

Use the helper for both “give me the output directory” and “give me a file path under outputs”.

Typical (conceptual) usage:

- Get the base directory:
  - `out_dir = output_dir()`  (returns a `Path`)
- Build a path under it:
  - `path = output_path("reports", "run.json")`
- Ensure a directory exists before writing:
  - `path.parent.mkdir(parents=True, exist_ok=True)` (or helper does it, depending on API)

Always write artifacts using `Path` objects (preferred) or strings derived from them.

## Migration guide (from old behavior)

Search and replace patterns to remove:

1. **Absolute `/outputs` paths** (forbidden):
   - Before: `open("/outputs/result.json", "w")`
   - After: `open(output_path("result.json"), "w")`

2. **Hard-coded relative outputs** (must be centralized):
   - Before: `Path("outputs") / "plot.png"`
   - After: `output_path("plot.png")`

3. **Ad hoc directory creation** scattered in code:
   - Before: `Path("outputs").mkdir(...)`
   - After: `output_dir().mkdir(...)` or rely on helper’s creation semantics.

4. **Tests**:
   - Tests should validate behavior by setting `OUTPUT_DIR` and calling the helper.
   - Avoid using `/outputs` in test fixtures; tests must fail if code attempts it.

## CI/CD enforcement

CI runs the test suite, including guard tests that:
- verify default resolution to `./outputs`,
- verify `OUTPUT_DIR` override behavior,
- ensure directories are created as expected,
- reject absolute `/outputs` targets,
- fail the build if any tracked source/test code contains attempts to write to absolute `/outputs`.

If a pipeline step needs a custom output location, set `OUTPUT_DIR` for that job/step rather than changing code.
