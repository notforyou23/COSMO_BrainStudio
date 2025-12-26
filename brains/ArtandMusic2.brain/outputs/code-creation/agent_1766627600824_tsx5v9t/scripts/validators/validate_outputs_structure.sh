#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

usage() {
  cat <<EOF
Usage: ${SCRIPT_NAME} [OUTPUTS_DIR]

Validates required /outputs directory structure and core artifacts.
If OUTPUTS_DIR is not provided, defaults to: \${REPO_ROOT}/outputs
EOF
}

log() { printf '[%s] %s
' "${SCRIPT_NAME}" "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

OUTPUTS_DIR="${1:-"${OUTPUTS_DIR:-"${REPO_ROOT}/outputs"}"}"
OUTPUTS_DIR="$(cd "${OUTPUTS_DIR}" 2>/dev/null && pwd || true)"

if [[ -z "${OUTPUTS_DIR}" || ! -d "${OUTPUTS_DIR}" ]]; then
  die "Outputs directory not found. Provide as arg or set OUTPUTS_DIR. Expected default: ${REPO_ROOT}/outputs"
fi

require_file() {
  local p="$1"
  [[ -f "${p}" ]] || die "Missing required file: ${p}"
  [[ -s "${p}" ]] || die "Required file is empty: ${p}"
}

require_dir() {
  local p="$1"
  [[ -d "${p}" ]] || die "Missing required directory: ${p}"
}

require_dir_nonempty() {
  local p="$1"
  require_dir "${p}"
  local count
  count="$(find "${p}" -mindepth 1 -maxdepth 1 -type f 2>/dev/null | wc -l | tr -d ' ')"
  [[ "${count}" -gt 0 ]] || die "Required directory is empty: ${p}"
}

find_pilot_dir() {
  local base="${OUTPUTS_DIR}"
  local candidates=(
    "${base}/pilot_case"
    "${base}/pilot-case"
    "${base}/pilot"
    "${base}/pilotcase"
  )
  local c
  for c in "${candidates[@]}"; do
    if [[ -d "${c}" ]]; then
      printf '%s' "${c}"
      return 0
    fi
  done
  return 1
}

log "Validating outputs structure under: ${OUTPUTS_DIR}"

require_file "${OUTPUTS_DIR}/REPORT_OUTLINE.md"
require_dir_nonempty "${OUTPUTS_DIR}/templates"

PILOT_DIR="$(find_pilot_dir || true)"
if [[ -z "${PILOT_DIR}" ]]; then
  die "Missing pilot case directory. Expected one of: ${OUTPUTS_DIR}/{pilot_case,pilot-case,pilot,pilotcase}"
fi

# Ensure pilot directory contains at least one meaningful artifact
pilot_files="$(find "${PILOT_DIR}" -type f 2>/dev/null | wc -l | tr -d ' ')"
[[ "${pilot_files}" -gt 0 ]] || die "Pilot case directory exists but has no files: ${PILOT_DIR}"

# Encourage machine-checkable naming without being overly strict
if ! find "${PILOT_DIR}" -maxdepth 2 -type f \( -iname '*.md' -o -iname '*.json' -o -iname '*.yaml' -o -iname '*.yml' -o -iname '*.txt' \) >/dev/null 2>&1; then
  die "Pilot case directory has no recognizable artifacts (*.md/*.json/*.y{a,}ml/*.txt): ${PILOT_DIR}"
fi

log "OK: outputs structure looks valid."
exit 0
