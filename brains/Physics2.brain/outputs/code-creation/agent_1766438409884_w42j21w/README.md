# generated_library_1766438416249 — Benchmark schema reference implementation

This project is a tiny, *reference* Python implementation for loading a benchmark JSON Schema and validating benchmark run JSON files against it. It is intended to be readable and easy to adapt, not feature-complete.

## What’s included

- `benchmarks.schema`: loads the repository’s JSON Schema (as a Python `dict`) and configures reference resolution so `$ref` works when the schema is split across files.
- `benchmarks.validate`: validates a benchmark run JSON document and returns a human-friendly error report (path + message).
- A CLI entry point (from `pyproject.toml`) for validating run files from the command line.
- An example dataset and expected validator outputs under:
  - `examples/` (sample run JSONs)
  - `outputs/` (expected “ok” and “error” output text)

## Installation

From the repository root:

```bash
python -m pip install -e .
```

Dependencies are intentionally minimal (primarily `jsonschema`).

## Validating a benchmark run

### CLI

Validate a run JSON file:

```bash
benchmarks-validate examples/run.valid.json
```

If the file is valid, the command exits with code `0` and prints a short success message.
If invalid, it exits non-zero and prints each validation error on its own line.

You can also run the module directly (useful during development):

```bash
python -m benchmarks.validate examples/run.invalid.json
```

### Python API

```python
from benchmarks.validate import validate_run_file

ok, errors = validate_run_file("examples/run.valid.json")
if not ok:
    for e in errors:
        print(e)
```

## Worked example (what the example dataset demonstrates)

The example folder contains two representative files:

- `examples/run.valid.json`  
  Demonstrates a minimal, schema-conformant benchmark run: required top-level metadata, at least one benchmark task, and at least one result record with required fields.

- `examples/run.invalid.json`  
  Demonstrates common failures (e.g., missing required properties, wrong types, unexpected enum values). The corresponding expected validator output lives in `outputs/run.invalid.expected.txt` so you can confirm the validator’s error formatting is stable.

To compare your local output with the expected output:

```bash
benchmarks-validate examples/run.invalid.json | diff -u outputs/run.invalid.expected.txt -
```

## Project layout (reference)

```
.
├── pyproject.toml
├── README.md
├── src/
│   └── benchmarks/
│       ├── __init__.py
│       ├── schema.py
│       └── validate.py
├── schema/                 # benchmark JSON Schema files live here
├── examples/               # sample benchmark runs
└── outputs/                # expected outputs for the sample runs
```

## Notes on schema resolution

The schema loader uses file-based resolution so that schemas can be factored into multiple files (via `$ref`). This keeps the schema maintainable while allowing validation to work in offline environments (no network fetches).
