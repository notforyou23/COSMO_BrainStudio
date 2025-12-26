# qg_bench

Minimal benchmark harness for question-generation (QG) style tasks.

It provides:
- **Dataset schema validation** via `jsonschema`
- A **single benchmark runner stub** that reads a dataset and emits deterministic JSON output
- One **worked example dataset** and an **expected-output fixture** used by CI

## Installation

From the repository root:

```bash
python -m pip install -e .
```

Or build/install normally:

```bash
python -m pip install .
```

After installation, the console entry point is:

```bash
qg-bench --help
```

## Dataset format (schema overview)

Datasets are JSON files validated against the bundled schema:
`src/qg_bench/schemas/benchmark.schema.json`.

At a high level the dataset is an object with:
- `benchmark_name` (string): Human-readable benchmark name
- `benchmark_version` (string): Dataset version (e.g., `"1.0"`)
- `items` (array): Each item is one example in the benchmark

Each item typically contains:
- `id` (string): Unique identifier within the dataset
- `context` (string): Source text from which a question could be generated
- `reference_question` (string): A gold/expected question (for simple fixtures)
- Optional metadata fields (object) depending on your use case

To see the authoritative definition, open the schema file listed above. Any dataset used by
the runner should validate against it.

## Validating a dataset

Validate a dataset JSON file against the bundled schema:

```bash
qg-bench validate path/to/dataset.json
```

If your environment does not expose the console script, you can also run validation as a module:

```bash
python -m qg_bench.validate path/to/dataset.json
```

Validation errors are reported with a clear JSON pointer/path to the failing field.

## Running the example benchmark

This repository includes a worked example dataset under `examples/`
(see the file names in that directory).

Run:

```bash
qg-bench run examples/example_benchmark.json
```

The runner prints a single JSON document to stdout containing:
- dataset identity (name/version)
- basic counts (e.g., number of items)
- any deterministic “stub” metrics computed by the runner

You can write the output to a file:

```bash
qg-bench run examples/example_benchmark.json > /tmp/qg_bench_output.json
```

## Expected-output fixtures and CI

To keep the benchmark runner deterministic and testable, CI checks that the example dataset
produces exactly the expected JSON output.

The expected output fixture lives under `tests/fixtures/` (see the file names there).
In CI, the workflow effectively does:

1. Run the benchmark on the example dataset to produce `actual.json`
2. Compare `actual.json` to the checked-in fixture (`expected.json`)
3. Fail if they differ (preventing accidental output/schema drift)

When you intentionally change runner output semantics, update the fixture accordingly and
ensure the example dataset still validates against the schema.
