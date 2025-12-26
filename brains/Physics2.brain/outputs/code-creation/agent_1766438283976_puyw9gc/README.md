# dgpipe

`dgpipe` is a small, typed Python toolkit for building and running **data-generation / data-processing pipelines** as composable stages.
It provides:
- a minimal domain model (pipeline specs, stage results),
- protocols (interfaces) to implement custom stages and runners,
- an ergonomic CLI to run pipelines from Python modules.

The project aims to stay lightweight, easy to extend, and safe to refactor (good typing, narrow public API).

## Install

From a local checkout:

```bash
python -m pip install -e .
```

Or run directly in a repo (for development):

```bash
python -m dgpipe --help
```

## Quick start (Python)

A pipeline is just a list of stages. A stage receives an input context and returns a result (or updated context).

```python
from dgpipe import Pipeline, Stage, run

class Hello(Stage):
    name = "hello"
    def __call__(self, ctx):
        ctx["greeting"] = f"hello {ctx.get('who','world')}"
        return ctx

pipe = Pipeline(stages=[Hello()])
final_ctx = run(pipe, {"who": "dgpipe"})
print(final_ctx["greeting"])
```

## CLI usage

The CLI is intended for running a pipeline defined in a Python module.

### 1) Create a pipeline module

Create `my_pipeline.py`:

```python
from dgpipe import Pipeline, Stage

class MakeNumber(Stage):
    name = "make_number"
    def __call__(self, ctx):
        ctx["n"] = 40 + 2
        return ctx

PIPELINE = Pipeline(stages=[MakeNumber()])
```

### 2) Run it

```bash
python -m dgpipe run my_pipeline:PIPELINE
```

Common options (exact flags may vary by version):
- `--input` to pass initial context (JSON),
- `--output` to write final context / results,
- `--verbose` for stage-by-stage logging.

Example:

```bash
python -m dgpipe run my_pipeline:PIPELINE --input '{"seed": 123}' --verbose
```

## Concepts

### Pipeline
A `Pipeline` is an ordered list of stages plus optional metadata (name, description, default config).

### Stage
A stage is a small, testable unit of work. Stages should:
- be deterministic where possible,
- validate inputs and produce well-scoped outputs,
- keep side effects explicit (e.g., writing files).

### Runner / execution
Execution is intentionally simple: stages run in order and pass a mutable context (dict-like) forward.
Runners can add behaviors like:
- structured logging,
- timing/metrics,
- retries,
- parallel execution (where safe).

## Extension points

`dgpipe` is designed to be extended without changing core code:

- **Custom stages**: implement the `Stage` protocol (callable) and optionally expose `name`.
- **Custom runners**: implement the runner protocol to control how stages are invoked and how results are collected.
- **Custom IO**: provide adapters for reading/writing contexts and artifacts (JSON, files, etc).

In general:
- depend on `dgpipe.protocols` for interfaces,
- depend on `dgpipe.models` for shared dataclasses,
- import from `dgpipe` (package root) for the stable public surface.

## Public API

The recommended imports are from the package root:

```python
from dgpipe import Pipeline, Stage, run
```

Lower-level modules are available for advanced use:
- `dgpipe.models` – core dataclasses / domain models
- `dgpipe.protocols` – typing protocols (interfaces)
- `dgpipe.cli` – CLI entrypoints

## Development

Run tests (if present):

```bash
python -m pytest
```

Type-check (if configured):

```bash
python -m mypy src
```

## License

See `LICENSE` in the repository root (if provided).
