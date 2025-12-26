#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
OUT_DIR="${OUT_DIR:-outputs}"
mkdir -p "${OUT_DIR}"

log() { printf '[ci_run] %s\n' "$*" >&2; }

run_optional() {
  local name="$1"; shift
  if "$@" >/dev/null 2>&1; then
    log "Running ${name}..."
    "$@"
    log "${name} OK"
    return 0
  fi
  log "Skipping ${name} (not available)"
  return 0
}

log "Python: $(${PYTHON_BIN} --version 2>&1)"

log "Upgrading pip/setuptools/wheel..."
${PYTHON_BIN} -m pip install -q --upgrade pip setuptools wheel

if [[ -f requirements.txt ]]; then
  log "Installing requirements.txt..."
  ${PYTHON_BIN} -m pip install -q -r requirements.txt
elif [[ -f pyproject.toml ]]; then
  log "Installing project (pyproject.toml detected)..."
  ${PYTHON_BIN} -m pip install -q .
else
  log "No requirements.txt or pyproject.toml found; proceeding without install step."
fi

# Formatting / lint checks (run only if tools are installed)
if ${PYTHON_BIN} -m ruff --version >/dev/null 2>&1; then
  log "Running ruff..."
  ${PYTHON_BIN} -m ruff check .
else
  log "Skipping ruff (not installed)"
fi

if ${PYTHON_BIN} -m black --version >/dev/null 2>&1; then
  log "Running black --check..."
  ${PYTHON_BIN} -m black --check .
else
  log "Skipping black (not installed)"
fi

if ${PYTHON_BIN} -m isort --version >/dev/null 2>&1; then
  log "Running isort --check-only..."
  ${PYTHON_BIN} -m isort --check-only .
else
  log "Skipping isort (not installed)"
fi

log "Running tests (pytest)..."
set +e
${PYTHON_BIN} -m pytest -q 2>&1 | tee "${OUT_DIR}/test.log"
test_rc=${PIPESTATUS[0]}
set -e
if [[ ${test_rc} -ne 0 ]]; then
  log "Tests failed with exit code ${test_rc}"
  exit ${test_rc}
fi
log "Tests OK"

log "Running evidence-pack pipeline..."
if [[ -f src/pipeline.py ]]; then
  set +e
  ${PYTHON_BIN} -m src.pipeline 2>&1 | tee "${OUT_DIR}/run.log"
  pipe_rc=${PIPESTATUS[0]}
  set -e
  if [[ ${pipe_rc} -ne 0 ]]; then
    log "Pipeline failed with exit code ${pipe_rc}"
    exit ${pipe_rc}
  fi
else
  log "ERROR: src/pipeline.py not found"
  exit 2
fi

# Minimal artifact presence checks (pipeline is expected to produce these)
req=( "${OUT_DIR}/results.json" "${OUT_DIR}/figure.png" "${OUT_DIR}/run.log" "${OUT_DIR}/test.log" "${OUT_DIR}/STATUS.md" )
for f in "${req[@]}"; do
  if [[ ! -f "${f}" ]]; then
    log "ERROR: missing required artifact: ${f}"
    exit 3
  fi
done

log "CI run complete; evidence pack artifacts present in ${OUT_DIR}/"
