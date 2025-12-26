#!/usr/bin/env bash
set -euo pipefail

# QA runner shell wrapper for CI and local workflows.
# Delegates to the standardized Python entrypoint: python -m qa.run
# All arguments are passed through verbatim.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd -- "${REPO_ROOT}"

choose_python() {
  if [[ -n "${QA_PYTHON:-}" ]]; then
    echo "${QA_PYTHON}"
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    echo "python"
    return 0
  fi
  echo "ERROR: No python interpreter found (set QA_PYTHON to override)." >&2
  return 127
}

PY_BIN="$(choose_python)"
exec "${PY_BIN}" -m qa.run "$@"
