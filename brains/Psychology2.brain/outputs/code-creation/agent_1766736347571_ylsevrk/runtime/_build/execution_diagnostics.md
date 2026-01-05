# Execution diagnostics: recurring “Container lost”

## Symptom
Multiple CodeExecutionAgent runs abort early with “Container lost” (execution stops before any test files are exercised). This pattern strongly indicates the runtime/container is being killed by the host (resource pressure or crash), not a deterministic test failure inside the project.

## Most likely root causes (ranked)
1) **Out-of-memory kill (OOM) during environment setup**
   - `pip install` can spike RAM (dependency resolver + building wheels, especially for scientific stacks, crypto, lxml, pandas/numpy, etc.).
   - OOM kills are abrupt and often show up externally as “container lost” rather than a Python traceback.

2) **Non-deterministic dependency resolution / source builds**
   - Unpinned dependencies cause the resolver to explore many combinations.
   - Missing wheels for the platform/Python version triggers compilation from source (high CPU/RAM, longer runtime, higher failure probability).

3) **Excessive disk usage / inode pressure**
   - Repeated installs without caching limits, large build artifacts, or large model/data downloads can exhaust ephemeral disk.

4) **Runaway logging / huge stdout**
   - Printing large dataframes, tensors, or verbose build logs can exceed platform output limits and destabilize the session.

5) **Architecture / platform mismatch**
   - Installing packages that pull incompatible wheels (e.g., manylinux vs macos, arm64 vs x86_64) can lead to repeated build attempts or crashes.

## Concrete remediation (make smoke tests reliable)
### A. Pin and constrain dependencies (primary fix)
- Use a **small `requirements.txt`** with compatible ranges and a **fully pinned `constraints.txt`** for determinism.
- Install with:
  - `python -m pip install -U pip setuptools wheel`
  - `python -m pip install -r requirements.txt -c constraints.txt --prefer-binary`
- Prefer binary wheels:
  - Add `--only-binary=:all:` where feasible (or selectively for heavy packages).
- Avoid optional extras unless needed for smoke tests.

### B. Pin the runtime image + Python toolchain
- Build/run smoke tests in a pinned Docker image:
  - Base image pinned by digest or exact tag (e.g., `python:3.11.9-slim-bookworm` or digest).
  - Install OS build deps explicitly (or avoid by using wheels).
- Set conservative environment knobs:
  - `PIP_DISABLE_PIP_VERSION_CHECK=1`
  - `PIP_DEFAULT_TIMEOUT=100`
  - `PIP_NO_CACHE_DIR=1` (or manage cache explicitly)
  - `PIP_PROGRESS_BAR=off`

### C. Reduce peak memory during install
- Prefer `--prefer-binary` and constraints to avoid source builds.
- If source builds are unavoidable:
  - Install build essentials only when required, then remove.
  - Limit parallel builds (where supported) and avoid `pip -vv` in CI.

### D. Limit runtime side-effects in smoke tests
- Ensure the smoke test:
  - Does not download large assets by default.
  - Does not generate massive logs.
  - Has clear timeouts and minimal data.

### E. Observability: capture enough evidence on failure
- In CI/Docker, capture:
  - `python -V`, `pip -V`, `pip freeze`
  - `df -h`, `free -m` (or `/proc/meminfo`)
  - Exit codes and the last ~200 lines of install/test output
- If Docker is used, check for OOM:
  - `docker inspect <cid> --format '{{.State.OOMKilled}} {{.State.ExitCode}}'`

## Verification checklist (run in order)
1) **Sanity**: container boots and prints versions quickly
   - `python -V && pip -V`
2) **Deterministic install** (no long resolver, no source builds unless expected)
   - `pip install -r requirements.txt -c constraints.txt --prefer-binary`
3) **No large downloads** during smoke test
   - environment variables set to disable model/data downloads (if applicable)
4) **Smoke test completes under resource limits**
   - verify runtime < expected wall time and stable memory
5) **Re-run** twice to confirm reproducibility
   - identical dependency set (`pip freeze` matches) and stable outcomes

## Expected outcome after fixes
With pinned Python/base image + deterministic dependency constraints + “prefer wheels”, the environment setup becomes stable and low-variance, eliminating the most common causes of “Container lost” (OOM / long resolver / source builds).
