#!/usr/bin/env bash
set -Eeuo pipefail

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }
log() { echo "[$(ts)] [entrypoint] $*"; }
err() { echo "[$(ts)] [entrypoint] ERROR: $*" >&2; }
die() { err "$*"; exit 111; }

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." >/dev/null 2>&1 && pwd -P || true)"
if [[ -z "${ROOT_DIR}" || ! -d "${ROOT_DIR}" ]]; then
  die "Unable to determine repo root from entrypoint location."
fi
cd "${ROOT_DIR}" || die "Failed to cd to repo root: ${ROOT_DIR}"

PY_BIN=""
if command -v python3 >/dev/null 2>&1; then PY_BIN="python3"
elif command -v python >/dev/null 2>&1; then PY_BIN="python"
else die "Python is not available in PATH. Install python3 and retry."
fi

log "Repo root: ${ROOT_DIR}"
log "Working dir: $(pwd -P)"
log "Python: $(${PY_BIN} -V 2>&1 || true)"
log "UID:GID = $(id -u):$(id -g) ($(id -un 2>/dev/null || true):$(id -gn 2>/dev/null || true))"

PREFLIGHT="scripts/preflight_smoke.py"
if [[ -f "${PREFLIGHT}" ]]; then
  log "Running preflight: ${PREFLIGHT}"
  set +e
  "${PY_BIN}" "${PREFLIGHT}"
  rc=$?
  set -e
  if [[ $rc -ne 0 ]]; then
    err "Preflight failed (exit=${rc}). This is likely the cause of 'Container lost' during test startup."
    err "Fix the reported issue(s) above (disk space, permissions, cwd, repo root), then retry."
    exit $rc
  fi
  log "Preflight passed."
else
  err "Preflight script not found at ${PREFLIGHT}. Skipping diagnostics."
  err "Consider adding it to surface early failures instead of silent container termination."
fi

if [[ $# -eq 0 ]]; then
  log "No command provided; starting interactive shell."
  exec bash
fi

log "Delegating to command: $*"
exec "$@"
