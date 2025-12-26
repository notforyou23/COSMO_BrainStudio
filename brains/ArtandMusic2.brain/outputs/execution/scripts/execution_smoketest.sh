#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PY_SCRIPT="${SCRIPT_DIR}/execution_smoketest.py"

DEFAULT_QA_DIR="/outputs/qa"
FALLBACK_QA_DIR="${PROJECT_ROOT}/outputs/qa"

QA_DIR="${QA_DIR:-$DEFAULT_QA_DIR}"
if ! mkdir -p "${QA_DIR}" 2>/dev/null; then
  QA_DIR="${FALLBACK_QA_DIR}"
  mkdir -p "${QA_DIR}"
fi

timestamp() {
  if command -v date >/dev/null 2>&1; then
    date -u +"%Y%m%dT%H%M%SZ" 2>/dev/null || true
  fi
}

TS="$(timestamp)"
if [[ -z "${TS}" ]]; then
  TS="$(python3 - <<'PY'
import datetime
print(datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"))
PY
)"
fi

LOG_PATH="${QA_DIR}/execution_smoketest_${TS}.log"
ENV_JSON_PATH="${QA_DIR}/execution_env.json"

export EXECUTION_SMOKETEST_TS="${TS}"
export EXECUTION_SMOKETEST_LOG_PATH="${LOG_PATH}"
export EXECUTION_SMOKETEST_ENV_JSON_PATH="${ENV_JSON_PATH}"
export PYTHONUNBUFFERED=1

if [[ ! -f "${PY_SCRIPT}" ]]; then
  echo "FATAL: missing smoke test python script: ${PY_SCRIPT}" | tee -a "${LOG_PATH}" >&2
  exit 2
fi

cd "${PROJECT_ROOT}"

set +e
python3 "${PY_SCRIPT}" "$@" 2>&1 | tee -a "${LOG_PATH}"
rc=${PIPESTATUS[0]}
set -e

exit "${rc}"
