# DOI fixture integration test

This integration test runs the DOI processing path end-to-end (via `api_server.py` or the CLI wrapper used by the test runner) against a small, fixed list of DOI fixtures and persists deterministic artifacts for debugging and CI review.

## What this test is (and is not)

- **Is**: a minimal, repeatable smoke test that the DOI pipeline can be invoked, returns structured results, and matches an explicit expected success/failure outcome per fixture.
- **Is not**: a comprehensive correctness suite for metadata quality; it only asserts high-level outcome stability (success vs expected failure) and captures artifacts for inspection.

## Inputs: the DOI fixture list

Fixture file:
- `tests/fixtures/doi_fixture_list.json`

Each fixture entry includes:
- `doi`: the DOI string to query/process
- `expected`: `"success"` or `"failure"`
- `notes`: rationale for expectation (e.g., known 404, malformed DOI, provider rate limits)
- Optional extra metadata (e.g., tags) as defined by the fixture schema

Expectation policy:
- A fixture marked `"success"` must yield a successful tool/pipeline result with the required top-level fields populated by the runner (at minimum: DOI echoed back and a success indicator).
- A fixture marked `"failure"` must fail in a controlled, explainable way (e.g., HTTP 404/410, invalid DOI format, upstream timeout) and must not crash the server/runner.

## How to run locally

From repo root:

1) Run only this integration test:
- `python -m pytest -q tests/integration/test_doi_fixture_integration.py -k doi_fixture`

2) Run with verbose output:
- `python -m pytest -vv tests/integration/test_doi_fixture_integration.py`

Environment notes:
- The test is written to run deterministically without interactive input.
- If the pipeline requires API keys, set them exactly as you would for normal tool use; the test will record missing/invalid credentials as controlled failures (and those fixtures should be marked accordingly until stabilized).

## Artifact output locations

The runner writes artifacts to **one** of these locations (chosen deterministically):
1) `outputs/tools/doi_fixture_integration/` (preferred when present)
2) `runtime/_build/doi_fixture_integration/` (fallback)

Within the chosen directory, the run should emit:
- `run.json`: run metadata (timestamp, git info if available, command invoked, environment summary)
- `results.json`: full structured results for each DOI fixture
- `results.csv`: flattened summary for quick triage (doi, expected, observed, status, error_class, error_message, duration_ms, etc.)
- Optional logs (e.g., `server.log`) if the runner started `api_server.py` as a subprocess

These artifacts are intended to be uploaded by CI on failure for debugging.

## Expected pass/fail cases (and rationale)

The fixture list must explicitly document why each case is expected to succeed or fail. Common categories:

Expected **success** (should pass consistently):
- Well-formed DOI that resolves via the primary provider(s)
- DOI with stable metadata access and no authentication requirement (or credentials present in CI)

Expected **failure** (still a passing test when it fails as expected):
- Malformed DOI (validation error)
- Known non-existent DOI (HTTP 404/410)
- Known upstream blocks that are reliably reproducible and documented (e.g., consistent 403 for a provider without credentials)

Unacceptable outcomes (test fails):
- Crash/hard exception without a structured error result
- A `"success"` fixture observed as failure (regression)
- A `"failure"` fixture observed as success (fixture is outdated; update expected outcome + rationale)
- Nondeterministic outcomes for the same fixture across repeated runs without a documented transient label

## Stability and CI gating criteria

This test is designed to be wired into CI once stable. Suggested stabilization process:

1) **Local burn-in**: run 10 times locally; outcomes must match expectations for every fixture.
2) **CI burn-in (non-gating)**: enable in CI but do not fail the build for N runs (e.g., 20). Upload artifacts on mismatch.
3) **Gating**: once mismatch rate is 0 over the burn-in window, make the job required.

To keep CI reliable:
- Keep the fixture list small (e.g., 5–15 DOIs).
- Prefer fixtures that do not require fragile network paths. If network is unavoidable, explicitly mark failures that represent known, stable constraints and ensure the runner reports them consistently.
- If rate limiting occurs, reduce concurrency in the runner and/or add backoff; record duration in artifacts.

## Interpreting failures

When the test fails, inspect:
- `results.csv` for a quick expected vs observed view
- `results.json` for full payloads and error details
- `run.json` for environment and command context

Typical remediation:
- If observed outcome changed due to upstream behavior: update fixture `expected` and `notes` **only if** the new behavior is stable and acceptable.
- If the tool regressed: fix the tool and keep fixture expectations unchanged.

## Determinism and reproducibility guarantees

The runner is expected to:
- Use a fixed artifact directory name (`doi_fixture_integration`) and stable filenames
- Record the invoked command and versions in `run.json`
- Ensure server subprocess lifecycle is managed (start, readiness check, stop) when using `api_server.py`
- Produce structured per-fixture results even on error
