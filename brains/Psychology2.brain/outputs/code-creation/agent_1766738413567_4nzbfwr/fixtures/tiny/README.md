# Tiny fixture dataset (CI)

This directory contains a *minimal, deterministic* fixture used by CI to exercise the project's canonical runner end-to-end. The goal is not realism; it is to reliably produce a small but complete set of pipeline outputs so CI can validate that the build layout, basic file integrity, and lightweight schemas remain stable over time.

## What CI does with this fixture

In the GitHub Actions workflow, CI will:

1. Run the canonical runner using `fixtures/tiny/config.yml`.
2. Write outputs into `runtime/_build/` (within the repo workspace).
3. Validate that these required subdirectories exist and are non-empty:

- `runtime/_build/reports/`
- `runtime/_build/tables/`
- `runtime/_build/figures/`
- `runtime/_build/logs/`

4. Apply lightweight checks (implemented in `scripts/ci_validate_build.py`), such as:
- tables are parseable (e.g., CSV/TSV have headers; JSON is decodable when present),
- logs are UTF-8 decodable and non-empty,
- figures are valid images (e.g., PNG/JPEG can be opened/verified),
- reports are non-empty and of expected basic type(s) (e.g., HTML/Markdown/PDF when present).
5. Upload the entire `runtime/_build/` directory as a CI artifact on every run for debugging and reproducibility.

## Files in this fixture

- `input.csv` — a tiny, deterministic input dataset intended to cover the runner's “happy path” with the smallest possible runtime.
- `config.yml` — minimal configuration pointing the canonical runner at `input.csv` and directing outputs to `runtime/_build/`.

## Determinism guarantees (by convention)

This fixture is designed to be stable across runs and platforms:

- Small inputs: only a handful of rows to keep execution fast.
- No randomness: the pipeline should avoid non-seeded randomness when using this fixture.
- Fixed paths: outputs are routed to `runtime/_build/` so CI can validate and archive them consistently.

If the canonical runner inherently uses randomness, it should be configured (via `config.yml` or runner defaults) to use a fixed seed for CI.

## Running locally

From the repository root (or wherever the canonical runner is invoked), run the same command CI runs, pointing at `fixtures/tiny/config.yml`. After it finishes, inspect:

- `runtime/_build/reports/`
- `runtime/_build/tables/`
- `runtime/_build/figures/`
- `runtime/_build/logs/`

To reproduce CI validation locally, run:

- `python scripts/ci_validate_build.py --build-dir runtime/_build`

(Exact runner invocation flags may vary by project; the CI workflow is the authoritative reference for the command line.)

## When to update this fixture

Update `input.csv` and/or `config.yml` only when required to keep the canonical runner executing the full minimal pipeline. Any change here should preserve determinism and keep runtime small, since it impacts CI latency and reliability.
