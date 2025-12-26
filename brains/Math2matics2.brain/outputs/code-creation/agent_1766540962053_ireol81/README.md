# deterministic_runner

A small Python library + CLI that runs a deterministic computation and writes **fixed** output files:

- `/outputs/results.json`
- `/outputs/figure.png`

The entrypoint is designed for reproducibility: it seeds RNGs, avoids time-based filenames, and records a compact metadata block (Python + package versions, and git hash if available).
## Install

From a local checkout:

```bash
python -m pip install -e .
```

Or (if you prefer) build/install normally:

```bash
python -m pip install .
```
## Run (deterministic entrypoint)

A console script is exposed by the package (see `pyproject.toml`). From the project root:

```bash
deterministic-runner
```

By default the CLI writes outputs under an absolute `/outputs` directory (created if needed). If you are running in an environment where you should write relative to the current directory, use the CLI option (if exposed in your build) to set an output directory, e.g.:

```bash
deterministic-runner --output-dir ./outputs
```
## Outputs

### 1) `/outputs/results.json`

A stable JSON file containing **fixed keys**. The CLI always writes the same top-level structure so that downstream checks are easy.

Typical structure:

- `inputs`: configuration used for the run (including the seed)
- `results`: computed numeric values (deterministic for the same inputs/seed)
- `metadata`: reproducibility information (see below)

### 2) `/outputs/figure.png`

A deterministic plot produced from the computed data. The filename is always exactly `figure.png` (no timestamps).
## Metadata captured

The run records a small `metadata` object inside `results.json` with:

- `git_commit`: current git commit hash **if available** (otherwise `null`)
- `python_version`: `sys.version` / `platform.python_version()` style string
- `platform`: OS / architecture info (when available)
- `packages`: a mapping of selected package versions (e.g., `numpy`, `matplotlib`, and this package)

This is intended to be sufficient for tracing what produced a given output without making the JSON unstable (e.g., it avoids current time).
## Determinism notes

The entrypoint aims to be deterministic across runs by:

- Seeding Python’s `random` module
- Seeding NumPy’s RNG (if NumPy is installed/used)
- Setting `PYTHONHASHSEED` behavior consistently where possible
- Avoiding any time-dependent behavior (timestamps, random temp filenames) in outputs

For maximum reproducibility, run in a pinned environment (lockfile, or a fixed set of package versions).
## Programmatic usage

You can also import and call the library directly (API surface is intentionally small):

```python
from deterministic_runner.determinism import set_deterministic
set_deterministic(seed=0)

# Then run your computation / plotting logic as provided by the package.
```
