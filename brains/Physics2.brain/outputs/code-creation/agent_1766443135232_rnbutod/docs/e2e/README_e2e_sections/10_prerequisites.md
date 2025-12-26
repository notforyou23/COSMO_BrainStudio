## Prerequisites

This section lists the baseline environment assumptions for running the end-to-end (E2E) workflow locally or in CI. If your project has additional requirements (GPU, external services, large datasets), layer them on top of this baseline.
### Supported platforms

- **OS**: Linux or macOS recommended. Windows is supported if your tooling works under PowerShell/WSL, but CI parity is typically best with Linux.
- **Python**: Use the Python version pinned by the repo (e.g., `.python-version`, `pyproject.toml`, or CI config). If no pin exists, use **Python 3.10+**.
- **Shell tools**: `bash`, `git`, and standard build tooling for any compiled dependencies used by your Python packages.
### Repository checkout

- Clone the repository with full history if your E2E steps rely on version metadata (tags/commits).
- Ensure submodules (if any) are initialized and updated:
  - `git submodule update --init --recursive`
### Python environment

Use an isolated environment to avoid dependency conflicts.

Common options:
- `python -m venv .venv && source .venv/bin/activate`
- `conda create -n <env> python=<version> && conda activate <env>`

Recommended sanity checks:
- `python -V`
- `python -m pip -V`
### Dependencies

Install dependencies using the repo’s canonical method (prefer whatever CI uses).

Typical patterns (use the one that matches your repo):
- **pyproject/Poetry**: `poetry install --with dev`
- **pip + requirements**: `python -m pip install -r requirements.txt` (and optionally `-r requirements-dev.txt`)
- **pip + editable**: `python -m pip install -e ".[dev]"`

Notes:
- If the repo provides a CI-specific lockfile (e.g., `requirements-ci.txt`), prefer it for deterministic E2E runs.
- If your E2E suite uses browsers, containers, or native libs, install the corresponding system packages before Python deps.
### Configuration and secrets

E2E runs frequently require configuration that must **not** be committed to git.

- Store runtime configuration in one of:
  - environment variables (preferred in CI),
  - a local config file excluded by `.gitignore`,
  - a secrets manager (preferred for shared environments).
- Ensure the following are available **before** running E2E:
  - API keys / tokens for external services used by the workflow,
  - credentials for private package registries (if any),
  - access to required network endpoints (VPN, allowlists, etc.).

Security guidance:
- Do not print secrets to logs.
- Use “least privilege” credentials dedicated to test environments when possible.
### Data and network assumptions

- If the E2E workflow downloads artifacts or datasets, ensure:
  - outbound network access is allowed,
  - proxy settings are configured (if required),
  - sufficient disk space is available (datasets + caches + logs).
- If the E2E workflow depends on a database, queue, or object store:
  - confirm service endpoints and ports are reachable from the runner,
  - confirm the test namespace/bucket/schema exists or can be created by the workflow.
### Optional tooling (only if your E2E suite needs it)

- **Docker**: required if the E2E suite starts service containers (databases, mocks, etc.).
  - Verify: `docker --version` and the daemon is running.
- **Make**: if the repo uses `make e2e` or similar convenience targets.
- **Node.js**: if the E2E suite runs frontend tooling or Playwright/Cypress.
- **Cloud CLIs** (AWS/GCP/Azure): if the workflow provisions or interacts with cloud resources.
### CI parity checklist

For reproducible results between local and CI runs, align:
- Python version and dependency lockfiles,
- environment variables and config sources,
- working directory and relative paths (avoid assumptions about `pwd`),
- filesystem permissions (CI runners may have stricter defaults),
- timeouts and resource limits (CPU/RAM).
