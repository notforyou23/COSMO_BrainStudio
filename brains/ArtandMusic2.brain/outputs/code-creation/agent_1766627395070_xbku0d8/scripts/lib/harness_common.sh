#!/usr/bin/env bash
# Shared helper library for validation harness scripts.
# Usage: source "$(dirname "$0")/lib/harness_common.sh"

hc::is_tty() { [[ -t 2 ]]; }

hc::ts() { date +"%Y-%m-%dT%H:%M:%S%z"; }

hc::color() {
  local code="$1"
  if hc::is_tty; then printf "[%sm" "$code"; fi
}

hc::reset() { if hc::is_tty; then printf "[0m"; fi }

hc::log() {
  local level="$1"; shift
  local msg="$*"
  local c=""
  case "$level" in
    INFO) c="$(hc::color 36)";;
    WARN) c="$(hc::color 33)";;
    ERROR) c="$(hc::color 31)";;
    OK) c="$(hc::color 32)";;
    *) c="";;
  esac
  printf "%s %s[%s]%s %s
" "$(hc::ts)" "$c" "$level" "$(hc::reset)" "$msg" >&2
}

hc::info() { hc::log INFO "$@"; }
hc::warn() { hc::log WARN "$@"; }
hc::error() { hc::log ERROR "$@"; }
hc::ok() { hc::log OK "$@"; }

hc::die() {
  local code="${1:-1}"; shift || true
  hc::error "$*"
  exit "$code"
}

hc::require_cmd() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || hc::die 127 "Required command not found: $cmd"
}

hc::abspath() {
  local p="$1"
  if [[ -z "$p" ]]; then return 1; fi
  if command -v python3 >/dev/null 2>&1; then
    python3 - <<'PY' "$p"
import os, sys
print(os.path.abspath(sys.argv[1]))
PY
  else
    (cd "$(dirname "$p")" 2>/dev/null && printf "%s/%s
" "$(pwd -P)" "$(basename "$p")") || return 1
  fi
}

hc::this_file() {
  local src="${BASH_SOURCE[0]}"
  while [[ -h "$src" ]]; do
    local dir; dir="$(cd -P "$(dirname "$src")" && pwd)"
    src="$(readlink "$src")"
    [[ "$src" != /* ]] && src="$dir/$src"
  done
  printf "%s
" "$src"
}

hc::script_dir() { cd -P "$(dirname "$(hc::this_file)")" && pwd; }

hc::project_root() {
  local d; d="$(hc::script_dir)"
  cd "$d/../.." 2>/dev/null && pwd -P || return 1
}

hc::outputs_dir() {
  local root; root="$(hc::project_root)" || return 1
  printf "%s
" "${HARNESS_OUTPUTS_DIR:-"$root/outputs"}"
}
hc::require_file() {
  local p="$1"
  [[ -n "$p" ]] || hc::die 2 "require_file: missing path argument"
  [[ -f "$p" ]] || hc::die 2 "Missing required file: $p"
}

hc::require_dir() {
  local p="$1"
  [[ -n "$p" ]] || hc::die 2 "require_dir: missing path argument"
  [[ -d "$p" ]] || hc::die 2 "Missing required directory: $p"
}

hc::require_nonempty_file() {
  local p="$1"
  hc::require_file "$p"
  [[ -s "$p" ]] || hc::die 2 "Required file is empty: $p"
}

hc::require_glob_any() {
  local pattern="$1"
  [[ -n "$pattern" ]] || hc::die 2 "require_glob_any: missing glob pattern"
  shopt -s nullglob
  local matches=( $pattern )
  shopt -u nullglob
  (( ${#matches[@]} > 0 )) || hc::die 2 "No files matched required pattern: $pattern"
}

hc::assert_under_dir() {
  local base="$1" path="$2"
  base="$(hc::abspath "$base")" || hc::die 2 "Invalid base dir: $base"
  path="$(hc::abspath "$path")" || hc::die 2 "Invalid path: $path"
  [[ "$path" == "$base"/* || "$path" == "$base" ]] || hc::die 2 "Path not under base dir ($base): $path"
}

hc::run() {
  local label="$1"; shift
  [[ -n "$label" ]] || label="command"
  hc::info "Running: $label"
  "$@" || hc::die $? "Failed: $label"
}

hc::ensure_outputs_basics() {
  local outdir="${1:-"$(hc::outputs_dir)"}"
  hc::require_dir "$outdir"
  hc::require_nonempty_file "$outdir/REPORT_OUTLINE.md"
  hc::require_dir "$outdir/templates"
  hc::require_glob_any "$outdir/templates/*"
  hc::require_dir "$outdir/pilot_case"
  hc::ok "Required outputs artifacts present under: $outdir"
}
