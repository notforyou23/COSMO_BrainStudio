# Single-cycle Evidence Pack

This repo generates a deterministic “evidence pack” in one end-to-end pipeline run. The pack is a canonical set of artifacts under `/outputs/` that can be validated in CI.

## What the pipeline produces

Running the pipeline creates/overwrites:

- `outputs/results.json` — structured run results (metrics + metadata)
- `outputs/figure.png` — canonical plot derived from `results.json`
- `outputs/run.log` — structured text log from the pipeline run
- `outputs/test.log` — captured test output (when run via the suggested command below)
- `outputs/STATUS.md` — short status summary: what ran, where outputs are, and what passed

All outputs are written relative to the project root (the repository working directory).

## Quickstart

### 1) Run the pipeline

```bash
python -m src.pipeline
```

This runs the single-cycle pipeline end-to-end and writes the evidence pack into `./outputs/`.

### 2) Run tests and capture a test log

```bash
pytest -q | tee outputs/test.log
```

The smoke test validates that the pipeline can run and that the required evidence-pack artifacts are created and minimally valid.

## Determinism / reproducibility

The pipeline is intended to be deterministic across runs on the same platform:

- fixed seed(s) are used for any stochastic steps
- timestamps, if included in metadata, are captured in a reproducible/controlled way
- plotting uses consistent styling to produce a canonical `figure.png`

If you re-run the pipeline, expect the files in `outputs/` to be overwritten.

## CI/CD validation

CI is expected to:

1. run the pipeline (`python -m src.pipeline`)
2. run the test suite (`pytest`)
3. ensure the evidence pack exists and is valid:
   - required files present in `outputs/`
   - `results.json` is parseable JSON with expected keys
   - `figure.png` is created
   - `STATUS.md` indicates the run completed and tests passed

The authoritative checks live in `tests/test_pipeline_smoke.py`; the goal is to keep the pipeline + evidence pack stable so CI can gate changes reliably.

## Repository layout (relevant parts)

- `src/pipeline.py` — orchestrates the end-to-end run and writes `outputs/*`
- `src/plotting.py` — deterministic figure rendering helpers
- `src/io_utils.py` — logging + JSON IO + output-directory helpers
- `tests/test_pipeline_smoke.py` — smoke test for artifact creation and basic validity
