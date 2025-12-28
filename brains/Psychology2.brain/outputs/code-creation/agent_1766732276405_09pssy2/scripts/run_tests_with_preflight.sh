#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd)"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "ERROR: Neither 'python3' nor 'python' found on PATH. Install Python or fix PATH before running tests." >&2
  exit 2
fi

PREFLIGHT="${REPO_ROOT}/scripts/preflight_smoke.py"
if [[ ! -f "${PREFLIGHT}" ]]; then
  echo "ERROR: Preflight script not found: ${PREFLIGHT}" >&2
  echo "ACTION: Ensure scripts/preflight_smoke.py exists in the repo and is checked into source control." >&2
  exit 3
fi

echo "[preflight] running: ${PYTHON_BIN} ${PREFLIGHT}"
set +e
"${PYTHON_BIN}" "${PREFLIGHT}"
PREFLIGHT_RC=$?
set -e
if [[ ${PREFLIGHT_RC} -ne 0 ]]; then
  echo "ERROR: Preflight checks failed (exit ${PREFLIGHT_RC}); refusing to run tests to avoid mid-run container loss." >&2
  exit ${PREFLIGHT_RC}
fi

cd -- "${REPO_ROOT}"

if [[ $# -gt 0 ]]; then
  echo "[tests] running command: $*"
  exec "$@"
fi

# Default test command (no args). Prefer pytest if available.
if "${PYTHON_BIN}" -c "import pytest" >/dev/null 2>&1; then
  echo "[tests] running default: ${PYTHON_BIN} -m pytest -q"
  exec "${PYTHON_BIN}" -m pytest -q
fi

echo "ERROR: No test command provided and pytest is not installed/importable." >&2
echo "ACTION: Either pass an explicit test command (e.g., './scripts/run_tests_with_preflight.sh python -m unittest') or add pytest to dependencies." >&2
exit 4
