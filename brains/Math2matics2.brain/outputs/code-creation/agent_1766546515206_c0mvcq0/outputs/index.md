# outputs/

This directory contains the canonical artifacts produced by the repository's test run capture step (see **[README.md](README.md)** for how to run it locally and in CI).
## Quick links

- **How to run + CI notes:** [outputs/README.md](README.md)
- **Captured pytest console output:** `outputs/pytest_output.txt`
- **Structured run metadata:** `outputs/run_metadata.json`
## Canonical run artifacts

| Path | Produced by | Description |
|---|---|---|
| `outputs/pytest_output.txt` | `scripts/run_tests_and_capture.py` | Full captured `pytest` stdout/stderr for the run (useful for debugging and CI logs). |
| `outputs/run_metadata.json` | `scripts/run_tests_and_capture.py` | Machine-readable metadata about the run (timestamps, exit code, environment info, and other execution details). |
