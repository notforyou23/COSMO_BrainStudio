#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

LOG_DIR="${ROOT_DIR}/runtime/_build/logs"
mkdir -p "${LOG_DIR}"

_run_preflight="0"
if [[ "${RUN_PREFLIGHT:-}" == "1" ]]; then
  _run_preflight="1"
elif [[ "${CI:-}" == "true" || "${CI:-}" == "1" ]]; then
  _run_preflight="1"
elif [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
  _run_preflight="1"
elif [[ -n "${BUILDKITE:-}" || -n "${GITLAB_CI:-}" || -n "${CIRCLECI:-}" || -n "${JENKINS_URL:-}" ]]; then
  _run_preflight="1"
fi

if [[ "${SKIP_PREFLIGHT:-}" == "1" ]]; then
  _run_preflight="0"
fi

if [[ "${_run_preflight}" == "1" ]]; then
  PREFLIGHT="${ROOT_DIR}/scripts/preflight_diagnostics.py"
  if [[ -f "${PREFLIGHT}" ]]; then
    if command -v python3 >/dev/null 2>&1; then
      echo "[entrypoint] running preflight diagnostics (logs: ${LOG_DIR}/container_health.jsonl)" >&2
      python3 "${PREFLIGHT}"
    else
      echo "[entrypoint] python3 not found; skipping preflight diagnostics" >&2
    fi
  else
    echo "[entrypoint] preflight script not found at ${PREFLIGHT}; skipping" >&2
  fi
fi

if [[ "$#" -gt 0 ]]; then
  exec "$@"
fi

if [[ -x "${ROOT_DIR}/docker/healthcheck.sh" ]]; then
  exec "${ROOT_DIR}/docker/healthcheck.sh"
fi

exec bash
