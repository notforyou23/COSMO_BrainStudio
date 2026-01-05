#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd)"

cd "${REPO_ROOT}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
PREFLIGHT="${PREFLIGHT_SMOKE_PATH:-${REPO_ROOT}/scripts/preflight_smoke.py}"

if [[ ! -f "${PREFLIGHT}" ]]; then
  echo "ERROR: Preflight smoke test not found: ${PREFLIGHT}" >&2
  echo "ACTION: Ensure scripts/preflight_smoke.py exists in the repo and is readable." >&2
  exit 2
fi

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "ERROR: Python executable not found: ${PYTHON_BIN}" >&2
  echo "ACTION: Set PYTHON_BIN to a valid python (e.g., PYTHON_BIN=python3) or install python3." >&2
  exit 2
fi

echo "[preflight] Running smoke test..."
"${PYTHON_BIN}" "${PREFLIGHT}"

if [[ $# -gt 0 ]]; then
  echo "[tests] Running: $*"
  exec "$@"
fi

if [[ -n "${TEST_CMD:-}" ]]; then
  echo "[tests] Running TEST_CMD: ${TEST_CMD}"
  exec bash -lc "${TEST_CMD}"
fi

echo "[tests] No command provided; defaulting to: python -m pytest"
exec "${PYTHON_BIN}" -m pytest
