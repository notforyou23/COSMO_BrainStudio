#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

log() { printf '%s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

usage() {
  cat >&2 <<'EOF'
Usage: scripts/run_scaffold.sh [--] [generator-args...]

Runs the repository scaffold generator in a predictable way for the validation harness.

Resolution order:
  1) If SCAFFOLD_CMD is set, it is executed as a shell command.
  2) Otherwise, a generator script is auto-detected from common paths under repo root
     and invoked via python3.

Environment:
  SCAFFOLD_CMD   Full command to run scaffold generator (preferred when auto-detect fails)
  PYTHON         Python interpreter to use (default: python3)

Examples:
  SCAFFOLD_CMD="python3 tools/scaffold.py" scripts/run_scaffold.sh --outputs ./outputs
  scripts/run_scaffold.sh --outputs ./outputs
EOF
}

PYTHON_BIN="${PYTHON:-python3}"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ "${1:-}" == "--" ]]; then shift; fi

run_cmd() {
  local cmd="$1"; shift || true
  log "INFO: Running scaffold generator: ${cmd} $*"
  cd "${REPO_ROOT}"
  eval "${cmd} "$@""
}

if [[ -n "${SCAFFOLD_CMD:-}" ]]; then
  run_cmd "${SCAFFOLD_CMD}" "$@"
  exit $?
fi

candidates=(
  "scripts/generate_scaffold.py"
  "scripts/scaffold.py"
  "tools/generate_scaffold.py"
  "tools/scaffold.py"
  "scaffold.py"
  "generate_scaffold.py"
  "scaffold_generator.py"
  "scripts/run_scaffold.py"
)

found=""
for rel in "${candidates[@]}"; do
  if [[ -f "${REPO_ROOT}/${rel}" ]]; then
    found="${rel}"
    break
  fi
done

if [[ -z "${found}" ]]; then
  die "No scaffold generator found. Set SCAFFOLD_CMD to an explicit command (e.g., 'python3 tools/scaffold.py')."
fi

log "INFO: Auto-detected generator script: ${found}"
cd "${REPO_ROOT}"
exec "${PYTHON_BIN}" "${found}" "$@"
