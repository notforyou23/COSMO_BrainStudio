# Reproducibility & Environment Stabilization

This project is designed to avoid “container lost” / drifting-environment failures by:
- Pinning Python dependencies in a lock manifest
- Recording a minimal environment manifest (OS/Python/tooling expectations)
- Running a tiny smoke-test before executing validators/meta-analysis
- Persisting environment versions into JSON run logs for traceability

This README describes how the Docker build/run works, how the manifests are used, and where versions are recorded.
## Files (manifests + checks)

- `requirements.lock.txt`
  - Pinned Python dependency lock file (exact versions).
  - Used during Docker build to create a stable runtime environment.

- `environment.manifest.json`
  - Minimal expectations for reproducibility (example fields: target OS family, Python version range, required tooling).
  - Used by the runner/smoke-test to sanity-check the runtime and to record intent alongside observed versions.

- `docker/Dockerfile`
  - Builds a reproducible runner image.
  - Installs dependencies strictly from `requirements.lock.txt`.
  - Runs the smoke-test as a build-time or entrypoint gate before executing the JSON-driven pipeline.

- Smoke-test (tiny Python script/module invoked by Docker/runner)
  - Confirms Python starts, core imports succeed, and manifest expectations can be read.
  - Emits a compact “environment snapshot” to the JSON run log before running the pipeline.
## Docker usage

### Build
From the repository root:
- `docker build -t cosmo-runner -f docker/Dockerfile .`

Build principles:
- Install dependencies from `requirements.lock.txt` only (no unpinned upgrades).
- Prefer deterministic layers (copy manifests first, install, then copy source).
- Run the smoke-test during build (or as the container entrypoint) so failures surface early and consistently.

### Run
Typical run patterns:
- `docker run --rm -v "$PWD:/work" cosmo-runner <runner args>`
- If the pipeline reads a JSON “script” or “run spec”, mount it and pass its path as an argument/environment variable.

Recommended runtime flags:
- Avoid network access during runs if possible (prevents opportunistic downloads and drift).
- Keep output/log directories mounted and writeable so run logs persist outside the container.
## How manifests are used

### `requirements.lock.txt`
- Serves as the single source of truth for Python dependency versions.
- The Docker build should:
  1) install a specific pip/setuptools/wheel baseline (if needed),
  2) install from `requirements.lock.txt`,
  3) optionally verify with `pip check` to detect broken dependency trees.

### `environment.manifest.json`
- Records the intended environment constraints (what we expect).
- The smoke-test/runner should:
  - load the manifest,
  - validate key expectations (Python version, platform, critical tools/imports),
  - record both “expected” and “observed” values into the run log.
## Smoke-test expectations (minimal but effective)

The smoke-test should be intentionally small and fast (seconds, not minutes). A typical checklist:
- Print/record `sys.version`, `platform.platform()`, and `platform.machine()`
- Confirm required packages import successfully (the same set the validators/meta-analysis need)
- Confirm manifests exist and are parseable:
  - `requirements.lock.txt` present
  - `environment.manifest.json` valid JSON
- Optionally run:
  - `pip --version`
  - `pip check` (useful as a hard gate in CI/build)

If the smoke-test fails, the pipeline must stop before running validators/meta-analysis.
## Where versions are recorded in JSON run logs

Run logs should include an “environment” section (or similar) written *before* validators/meta-analysis start.
Recommended fields:

- `environment.observed.python.version`: `sys.version`
- `environment.observed.python.executable`: `sys.executable`
- `environment.observed.platform`: `platform.platform()`
- `environment.observed.machine`: `platform.machine()`
- `environment.observed.packages`: a reproducible package list (prefer `pip freeze` output)
- `environment.expected`: the parsed `environment.manifest.json` (or a subset)

This makes runs debuggable: if a future run diverges, you can compare the run’s recorded environment snapshot to the manifest and lock file.
## Determinism tips (practical)

- Treat `requirements.lock.txt` as immutable for a given release/run baseline.
- Rebuild the Docker image when the lock changes; tag images with a content hash or date.
- Keep `docker/.dockerignore` strict to avoid copying caches, artifacts, or local virtualenvs into the build context.
- Ensure the runner never performs “helpful” auto-installs at runtime; dependency resolution belongs in the build step.
- Record environment snapshots in every run log, even for failures, to speed up incident triage.
