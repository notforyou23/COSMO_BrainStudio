#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
cd "${REPO_ROOT}"

PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "ERROR: Python interpreter not found: ${PYTHON_BIN}" >&2
  exit 127
fi

# Canonical one-command QA gate harness: runs init_outputs then validate_outputs,
# and verifies required artifacts (TRACKING_RECONCILIATION.md, Claim Cards, QA gate artifacts).
exec "${PYTHON_BIN}" -m tools.pipeline "$@"
