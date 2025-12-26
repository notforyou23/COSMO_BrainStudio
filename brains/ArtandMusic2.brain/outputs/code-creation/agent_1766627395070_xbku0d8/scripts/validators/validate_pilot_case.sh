#!/usr/bin/env bash
set -euo pipefail

_me="$(basename "$0")"

log() { printf '%s\n' "$*" >&2; }
die() { log "ERROR: ${_me}: $*"; exit 1; }
note() { log "INFO: ${_me}: $*"; }

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../.." && pwd)"

outputs_dir="${OUTPUTS_DIR:-${repo_root}/outputs}"
[[ -d "$outputs_dir" ]] || die "outputs directory not found: ${outputs_dir} (set OUTPUTS_DIR to override)"

is_nonempty_file() { [[ -f "$1" ]] && [[ -s "$1" ]]; }

contains_any_marker() {
  local f="$1"; shift
  local m
  for m in "$@"; do
    if grep -Eiq "$m" "$f"; then return 0; fi
  done
  return 1
}

pick_pilot_path() {
  local base="$1"
  if [[ -n "${PILOT_CASE_DIR:-}" ]]; then
    local p="${PILOT_CASE_DIR}"
    [[ "$p" = /* ]] || p="${base}/${p}"
    [[ -e "$p" ]] || die "PILOT_CASE_DIR points to missing path: ${p}"
    printf '%s\n' "$p"
    return 0
  fi

  local candidates=(
    "${base}/pilot_case"
    "${base}/pilot-case"
    "${base}/pilot"
    "${base}/pilotcase"
    "${base}/case_study"
    "${base}/case-study"
    "${base}/pilot_case.md"
    "${base}/pilot-case.md"
    "${base}/PILOT_CASE.md"
  )
  local c
  for c in "${candidates[@]}"; do
    if [[ -e "$c" ]]; then
      printf '%s\n' "$c"
      return 0
    fi
  done

  local first_match=""
  first_match="$(find "$base" -maxdepth 2 -type d \( -iname '*pilot*' -o -iname '*case*' \) 2>/dev/null | head -n 1 || true)"
  if [[ -n "$first_match" ]]; then
    printf '%s\n' "$first_match"
    return 0
  fi

  return 1
}

pilot_path="$(pick_pilot_path "$outputs_dir" || true)"
[[ -n "$pilot_path" ]] || die "pilot case not found under ${outputs_dir} (expected e.g., outputs/pilot_case or set PILOT_CASE_DIR)"

note "using pilot case path: ${pilot_path}"

if [[ -f "$pilot_path" ]]; then
  is_nonempty_file "$pilot_path" || die "pilot case file is empty: ${pilot_path}"
  contains_any_marker "$pilot_path" 'pilot case' 'case study' '^#' '##' || die "pilot case file lacks recognizable markdown structure/headings: ${pilot_path}"
  contains_any_marker "$pilot_path" 'assumption' 'data source' 'method' 'scope' 'metric' 'evaluation' || die "pilot case file missing minimum content markers (assumptions/data sources/method/scope/metrics): ${pilot_path}"
  note "pilot case file validated"
  exit 0
fi

[[ -d "$pilot_path" ]] || die "pilot case path exists but is neither file nor directory: ${pilot_path}"

readme=""
for f in "${pilot_path}/README.md" "${pilot_path}/readme.md" "${pilot_path}/PILOT_CASE.md"; do
  if [[ -f "$f" ]]; then readme="$f"; break; fi
done
[[ -n "$readme" ]] || die "pilot case directory missing README.md (or PILOT_CASE.md): ${pilot_path}"
is_nonempty_file "$readme" || die "pilot case README exists but is empty: ${readme}"

contains_any_marker "$readme" '^#' '##' || die "pilot case README lacks markdown headings: ${readme}"
contains_any_marker "$readme" 'assumption' 'data source' 'method' 'scope' 'metric' 'evaluation' || die "pilot case README missing minimum content markers (assumptions/data sources/method/scope/metrics): ${readme}"

has_payload="no"
if [[ -d "${pilot_path}/data" || -d "${pilot_path}/inputs" || -d "${pilot_path}/artifacts" ]]; then
  has_payload="yes"
fi
if [[ "$has_payload" = "no" ]]; then
  if find "$pilot_path" -maxdepth 2 -type f \( -iname '*.csv' -o -iname '*.json' -o -iname '*.yaml' -o -iname '*.yml' -o -iname '*.parquet' \) 2>/dev/null | grep -q .; then
    has_payload="yes"
  fi
fi
[[ "$has_payload" = "yes" ]] || die "pilot case directory missing data/inputs/artifacts directory and no data-like files (*.csv/*.json/*.yml/*.parquet) found: ${pilot_path}"

note "pilot case directory validated"
