#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"

log() { printf '%s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

realpath_fallback() {
  local p="$1"
  python3 - <<'PY' "$p" 2>/dev/null || printf '%s\n' "$p"
import os,sys
print(os.path.realpath(sys.argv[1]))
PY
}

OUTPUTS_DIR="${OUTPUTS_DIR:-${ROOT_DIR}/outputs}"
OUTPUTS_DIR="$(realpath_fallback "${OUTPUTS_DIR}")"

SCaffold_run() {
  local ran="0"
  if [[ -n "${SCAFFOLD_CMD:-}" ]]; then
    log "Running scaffold generator via SCAFFOLD_CMD..."
    bash -lc "${SCAFFOLD_CMD}" || die "Scaffold generator failed (SCAFFOLD_CMD)."
    ran="1"
  elif [[ -f "${ROOT_DIR}/scripts/run_scaffold.py" ]]; then
    require_cmd python3
    log "Running scaffold generator: python3 scripts/run_scaffold.py"
    python3 "${ROOT_DIR}/scripts/run_scaffold.py" || die "Scaffold generator failed (scripts/run_scaffold.py)."
    ran="1"
  elif [[ -f "${ROOT_DIR}/scripts/run_scaffold.sh" ]]; then
    log "Running scaffold generator: bash scripts/run_scaffold.sh"
    bash "${ROOT_DIR}/scripts/run_scaffold.sh" || die "Scaffold generator failed (scripts/run_scaffold.sh)."
    ran="1"
  elif [[ -f "${ROOT_DIR}/Makefile" ]] && command -v make >/dev/null 2>&1; then
    if make -q scaffold >/dev/null 2>&1; then
      log "Running scaffold generator: make scaffold"
      make -C "${ROOT_DIR}" scaffold || die "Scaffold generator failed (make scaffold)."
      ran="1"
    fi
  fi

  if [[ "${ran}" != "1" ]]; then
    die "No scaffold generator found. Set SCAFFOLD_CMD or add scripts/run_scaffold.py or scripts/run_scaffold.sh (or Makefile target 'scaffold')."
  fi
}

require_path() {
  local p="$1"
  local hint="${2:-}"
  [[ -e "${p}" ]] || die "Missing required artifact: ${p}${hint:+ (${hint})}"
}

require_nonempty_file() {
  local p="$1"
  [[ -f "${p}" ]] || die "Missing required file: ${p}"
  [[ -s "${p}" ]] || die "Required file is empty: ${p}"
}

require_dir() {
  local p="$1"
  [[ -d "${p}" ]] || die "Missing required directory: ${p}"
}

run_validator() {
  local script="$1"
  [[ -f "${script}" ]] || die "Validator not found: ${script}"
  [[ -x "${script}" ]] || die "Validator not executable: ${script} (chmod +x)"
  log "Running validator: $(basename "${script}")"
  "${script}" "${OUTPUTS_DIR}" || die "Validator failed: ${script}"
}
main() {
  log "Validation harness starting..."
  log "ROOT_DIR=${ROOT_DIR}"
  log "OUTPUTS_DIR=${OUTPUTS_DIR}"

  SCaffold_run

  require_dir "${OUTPUTS_DIR}"
  require_nonempty_file "${OUTPUTS_DIR}/REPORT_OUTLINE.md"
  require_dir "${OUTPUTS_DIR}/templates"

  if [[ ! -e "${OUTPUTS_DIR}/pilot_case" && ! -e "${OUTPUTS_DIR}/pilot_case.md" && ! -e "${OUTPUTS_DIR}/pilot_case.json" && ! -e "${OUTPUTS_DIR}/pilot" ]]; then
    die "Missing pilot case artifact under outputs. Expected one of: pilot_case/ (dir), pilot_case.md, pilot_case.json, or pilot."
  fi

  VALIDATORS_DIR="${ROOT_DIR}/scripts/validators"
  require_dir "${VALIDATORS_DIR}"

  run_validator "${VALIDATORS_DIR}/validate_outputs_structure.sh"
  run_validator "${VALIDATORS_DIR}/validate_markdown_outline.sh"
  run_validator "${VALIDATORS_DIR}/validate_templates.sh"

  log "Validation harness completed successfully."
}

main "$@"
