# Outputs: benchmarks, schemas, and tests

This repository is designed to be runnable end-to-end: a small benchmark artifact (JSON) is validated against a JSON Schema and a reference computation is re-run to ensure the expected outputs are reproducible.

## What lives under `outputs/`

- `outputs/schemas/`
  - `benchmark.schema.json`: JSON Schema describing the required structure of benchmark artifacts.
- `outputs/examples/`
  - `benchmark_case_001.json`: A minimal example benchmark case used by tests/CI.
- `outputs/README.md` (this file): How to run the benchmark workflow and test suite.

## Local setup

This project uses a standard Python tooling stack:
- `pytest` for tests
- `jsonschema` for schema validation

Create a virtual environment and install dependencies (choose one approach):

### Option A: `pip` (recommended for CI parity)

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows (PowerShell):
# .venv\Scripts\Activate.ps1

python -m pip install -U pip
python -m pip install -e .
```

### Option B: `pip` without editable install

```bash
python -m pip install -U pip
python -m pip install -r requirements.txt
```

(If your project does not ship a `requirements.txt`, use Option A.)

## Run the full test suite

From the repository root:

```bash
pytest -q
```

The tests are expected to:
1. Load `outputs/examples/benchmark_case_001.json`
2. Validate it against `outputs/schemas/benchmark.schema.json`
3. Recompute the benchmark outputs deterministically
4. Compare the recomputed outputs to the expected outputs embedded in the example JSON

If any of these steps fail, `pytest` exits non-zero (and CI will fail).

## How CI runs

GitHub Actions (see `.github/workflows/ci.yml`) runs essentially the same commands:

1. Set up the requested Python version
2. Install the project (and test dependencies)
3. Run `pytest`

CI is intended to catch:
- Schema changes that invalidate existing benchmark artifacts
- Logic changes that break reproducibility of the example benchmark computation
- Accidental edits to expected outputs

## Notes on reproducibility

- Benchmark example JSON files should be fully self-contained and deterministic:
  - Avoid timestamps, random seeds without fixed values, or environment-dependent behavior.
- When updating the computation logic, update the example artifact only when the new outputs are intended and reviewed. Schema validation should still pass.

## Troubleshooting

- If schema validation fails: inspect the validation error path and compare your example JSON to `outputs/schemas/benchmark.schema.json`.
- If output comparison fails: ensure the computation uses only the inputs in the benchmark JSON and is deterministic across platforms.
