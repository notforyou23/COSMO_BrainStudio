# End-to-end (E2E) test runs

This document is the canonical reference for running E2E tests locally and in CI, and for understanding how failures are triaged and reported.

## What “E2E” means in this repo

E2E tests exercise the system in a production-like way (build + run + validate) rather than unit-level behavior.
They typically take longer, depend on more tooling, and produce artifacts useful for debugging (logs, screenshots, traces, etc.).

## Running E2E locally

### Prereqs

- Python (match the version used in CI when possible)
- The project’s normal dependencies (your standard development install)
- Any browser / driver / container runtime required by your E2E framework (project-specific)

### Install dependencies

- Local development dependencies are usually installed from the repo root (your normal workflow).
- CI-only dependencies used by E2E runs are documented in: `docs/e2e/requirements-ci.txt`.

If you want your local environment to mimic CI as closely as possible, install the CI set too:

```bash
python -m pip install -r docs/e2e/requirements-ci.txt
```

### Run

Run the project’s E2E command the same way CI does (see the workflow in `.github/workflows/` for the exact invocation).
Common patterns include:

```bash
# Example patterns only (use the workflow as the source of truth)
python -m pytest -m e2e
# or
make e2e
```

### Tips for reproducing CI locally

- Prefer a clean virtualenv (or fresh dependency install) when chasing a flaky failure.
- Set the same env vars the CI job sets (see `.github/workflows/e2e_failure.yml`).
- Re-run with increased logging (framework-specific) and preserve logs between runs.

## Running E2E in CI

E2E runs are executed via GitHub Actions.
The workflow is designed to be reusable and consistent across branches and triggers, while still capturing rich failure diagnostics.

### Where the workflow lives

- Workflow entry point: `.github/workflows/e2e_failure.yml`
- Shared setup logic (composite action): `.github/actions/e2e-common/action.yml`
- Failure-only diagnostics (composite action): `.github/actions/e2e-on-failure/action.yml`

### High-level job flow

1. Checkout repository
2. **Common setup** via `e2e-common`:
   - environment normalization (shell, paths, locale/timezone if needed)
   - dependency caching
   - install Python deps (including `docs/e2e/requirements-ci.txt` where applicable)
3. Run the E2E command
4. On failure, **triage** via `e2e-on-failure`:
   - collect diagnostics
   - bundle logs
   - upload artifacts
   - write a concise GitHub Actions job summary

## Failure triage: what gets captured and how to use it

When an E2E run fails, the CI job captures evidence to make failures actionable:

- **Artifacts**: uploaded bundles of logs and other runtime outputs
- **Console logs**: full job output for quick scanning
- **Step summary**: short “what failed / where to look” notes

### How to debug from CI artifacts

1. Open the failing workflow run in GitHub Actions.
2. Download uploaded artifacts from the run.
3. Inspect:
   - primary test runner output (often the fastest signal)
   - per-test logs/traces (if produced)
   - environment info captured during setup (versions, paths)

### Common failure classes

- Dependency drift: pinning mismatches or missing CI-only deps (check `docs/e2e/requirements-ci.txt`)
- Environment differences: OS / PATH / locale / permissions differences between local and runner
- Flaky external dependencies: network calls, rate limits, ephemeral services
- Timing issues: add retries/awaits at the right layer (test code vs system under test)

## Workflow modularization (why composite actions)

The E2E workflow is split into composite actions to reduce duplication and to keep behavior consistent:

- **`e2e-common`**: everything that should be identical across all E2E workflows
  (setup, caching, dependency installation, normalized environment).
- **`e2e-on-failure`**: everything that should only run when something fails
  (diagnostics, artifact upload, summaries).

This structure makes it easier to:
- update E2E infrastructure once and reuse it everywhere
- review changes (setup vs diagnostics vs test execution are clearly separated)
- add new E2E workflows without copy/paste

## Making changes safely

If you change E2E dependencies or the runtime environment:

- Update `docs/e2e/requirements-ci.txt` when CI-only packages are added/removed/pinned.
- Prefer changing shared behavior inside the composite actions so all workflows stay consistent.
- Validate by running locally (if possible) and then confirming CI produces the expected artifacts on failure.

## Quick links

- Workflow: `.github/workflows/e2e_failure.yml`
- Composite actions:
  - `.github/actions/e2e-common/action.yml`
  - `.github/actions/e2e-on-failure/action.yml`
- CI requirements: `docs/e2e/requirements-ci.txt`
