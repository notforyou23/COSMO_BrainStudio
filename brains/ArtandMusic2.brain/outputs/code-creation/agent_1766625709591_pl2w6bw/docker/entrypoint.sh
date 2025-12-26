#!/usr/bin/env bash
set -euo pipefail

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
log() { echo "[$(ts)] [entrypoint] $*" >&2; }

export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"
umask 002

WORKDIR="${WORKDIR:-/app}"
OUT_DIR="${OUT_DIR:-/outputs}"
LOG_DIR="${LOG_DIR:-${OUT_DIR}/logs}"
ART_DIR="${ART_DIR:-${OUT_DIR}/artifacts}"

SMOKETEST="${SMOKETEST:-${WORKDIR}/scripts/container_health_smoketest.py}"
EXPECTATIONS="${EXPECTATIONS:-${WORKDIR}/scripts/artifact_expectations.json}"

mkdir -p "${OUT_DIR}" "${LOG_DIR}" "${ART_DIR}"

ENTRY_LOG="${LOG_DIR}/entrypoint.$(date -u +%Y%m%dT%H%M%SZ).log"
touch "${ENTRY_LOG}" || true
exec > >(tee -a "${ENTRY_LOG}") 2>&1

log "Starting. WORKDIR=${WORKDIR} OUT_DIR=${OUT_DIR} LOG_DIR=${LOG_DIR} ART_DIR=${ART_DIR}"
log "User=$(id -u):$(id -g) Host=$(hostname) PWD=$(pwd) Shell=${SHELL:-unknown}"

# Best-effort environment snapshot (do not fail on errors)
{
  echo "timestamp=$(ts)"
  echo "uname=$(uname -a || true)"
  echo "id=$(id || true)"
  echo "pwd=$(pwd || true)"
  echo "workdir=${WORKDIR}"
  echo "out_dir=${OUT_DIR}"
  echo "log_dir=${LOG_DIR}"
  echo "art_dir=${ART_DIR}"
  echo "--- env ---"
  env | sort
} > "${LOG_DIR}/runtime_env.txt" 2>/dev/null || true

# Ensure mounted volumes are writable; leave clear breadcrumbs if not
touch "${LOG_DIR}/.writable" 2>/dev/null || log "WARN: LOG_DIR not writable: ${LOG_DIR}"
touch "${ART_DIR}/.writable" 2>/dev/null || log "WARN: ART_DIR not writable: ${ART_DIR}"

if [[ ! -f "${SMOKETEST}" ]]; then
  log "ERROR: Smoke test script missing: ${SMOKETEST}"
  ls -la "${WORKDIR}/scripts" 2>/dev/null || true
  exit 127
fi

if [[ ! -f "${EXPECTATIONS}" ]]; then
  log "WARN: Expectations file missing: ${EXPECTATIONS} (smoketest may use defaults)"
fi

cd "${WORKDIR}" 2>/dev/null || {
  log "ERROR: Cannot cd to WORKDIR=${WORKDIR}"
  ls -la / 2>/dev/null || true
  exit 2
}

log "Invoking smoke test..."
python3 "${SMOKETEST}" \
  --workdir "${WORKDIR}" \
  --outdir "${OUT_DIR}" \
  --logdir "${LOG_DIR}" \
  --artifact-dir "${ART_DIR}" \
  --expectations "${EXPECTATIONS}" \
  ${SMOKETEST_ARGS:-}

rc=$?
log "Smoke test completed with rc=${rc}"

# Hard escalation if smoke test "succeeds" but expected artifacts/logs are missing
if [[ "${rc}" -eq 0 ]]; then
  missing=0
  [[ -d "${LOG_DIR}" ]] || missing=1
  [[ -d "${ART_DIR}" ]] || missing=1
  [[ -s "${ENTRY_LOG}" ]] || missing=1
  if [[ "${missing}" -ne 0 ]]; then
    log "ESCALATION: rc=0 but essential execution artifacts are missing (log/art directories or entry log)."
    exit 88
  fi
fi

exit "${rc}"
