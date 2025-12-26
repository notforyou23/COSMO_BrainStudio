#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../.." && pwd)"
outputs_dir="${OUTPUTS_DIR:-"${repo_root}/outputs"}"
outline_path="${outputs_dir}/REPORT_OUTLINE.md"

err() { echo "ERROR: $*" >&2; }
note() { echo "INFO: $*" >&2; }

require_file() {
  local p="$1"
  local label="$2"
  if [[ ! -e "$p" ]]; then
    err "Missing required ${label}: ${p}"
    return 1
  fi
  if [[ ! -f "$p" ]]; then
    err "Expected ${label} to be a file, but it is not: ${p}"
    return 1
  fi
  if [[ ! -s "$p" ]]; then
    err "Required ${label} exists but is empty: ${p}"
    return 1
  fi
  return 0
}

require_heading() {
  local p="$1"
  local heading_re="$2"
  local heading_label="$3"
  if ! grep -Eqi "${heading_re}" "$p"; then
    err "Missing required section heading (${heading_label}) in ${p}"
    err "Expected to find a line matching regex: ${heading_re}"
    return 1
  fi
  return 0
}

main() {
  require_file "${outline_path}" "outline markdown (REPORT_OUTLINE.md)"

  # Must start with an H1 title as the first non-empty line.
  local first_non_empty
  first_non_empty="$(grep -nE '^[[:space:]]*[^[:space:]]' "${outline_path}" | head -n1 || true)"
  if [[ -z "${first_non_empty}" ]]; then
    err "Outline has no non-empty lines: ${outline_path}"
    exit 1
  fi
  if ! echo "${first_non_empty}" | cut -d: -f2- | grep -Eq '^[[:space:]]*#[[:space:]]+[^#[:space:]].+'; then
    err "First non-empty line must be an H1 title (e.g., '# Report Title') in ${outline_path}"
    err "Found: $(echo "${first_non_empty}" | cut -d: -f2-)"
    exit 1
  fi

  # Minimal required sections (H2).
  require_heading "${outline_path}" '^[[:space:]]*##[[:space:]]+Executive[[:space:]]+Summary([[:space:]]|$)' "## Executive Summary"
  require_heading "${outline_path}" '^[[:space:]]*##[[:space:]]+Background([[:space:]]|$)' "## Background"
  require_heading "${outline_path}" '^[[:space:]]*##[[:space:]]+Methodology([[:space:]]|$)' "## Methodology"
  require_heading "${outline_path}" '^[[:space:]]*##[[:space:]]+Findings([[:space:]]|$)' "## Findings"
  require_heading "${outline_path}" '^[[:space:]]*##[[:space:]]+Recommendations([[:space:]]|$)' "## Recommendations"

  # Ensure the outline has enough structure for downstream tooling.
  local h2_count
  h2_count="$(grep -Eic '^[[:space:]]*##[[:space:]]+[^[:space:]]' "${outline_path}" || true)"
  if [[ "${h2_count}" -lt 5 ]]; then
    err "Outline appears under-structured: expected at least 5 H2 sections, found ${h2_count} in ${outline_path}"
    exit 1
  fi

  note "validate_markdown_outline: OK (${outline_path})"
}

main "$@"
