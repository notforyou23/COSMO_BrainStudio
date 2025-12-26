#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-$PWD}"
if [[ -d "/outputs" ]]; then
  BASE_OUT="/outputs"
else
  BASE_OUT="${ROOT_DIR}/outputs"
fi

LOG_DIR="${QA_EXEC_LOG_DIR:-${BASE_OUT}/qa/exec_logs}"
mkdir -p "${LOG_DIR}"

ts="$(date -u +%Y%m%dT%H%M%SZ)"
log_file="${LOG_DIR}/qa_run_${ts}.log"

export QA_EXEC_LOG_DIR="${LOG_DIR}"
export QA_ENV_DUMP_DIR="${LOG_DIR}"
export PYTHONUNBUFFERED=1

python_bin="${PYTHON_BIN:-python3}"
runner="${QA_RUNNER:-${ROOT_DIR}/scripts/qa_run.py}"

if [[ ! -f "${runner}" ]]; then
  echo "ERROR: QA runner not found: ${runner}" >&2
  echo "LOG_DIR=${LOG_DIR}" >&2
  exit 2
fi

echo "QA_ENTRYPOINT: runner=${runner} log_file=${log_file}" >&2

set +e
("${python_bin}" -u "${runner}" "$@") 2>&1 | tee -a "${log_file}"
rc=${PIPESTATUS[0]}
set -e

echo "QA_ENTRYPOINT: exit_code=${rc} log_file=${log_file}" >&2
exit "${rc}"
