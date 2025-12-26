#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

CANONICALIZE_PY="${ROOT_DIR}/scripts/canonicalize_outputs.py"
if [[ ! -f "${CANONICALIZE_PY}" ]]; then
  echo "ERROR: canonicalization CLI not found: ${CANONICALIZE_PY}" >&2
  exit 2
fi

mkdir -p "${ROOT_DIR}/outputs/qa" "${ROOT_DIR}/outputs/tracking"

HELP_TEXT="$("${PYTHON_BIN}" "${CANONICALIZE_PY}" --help 2>&1 || true)"

declare -a ARGS=()
if grep -qE '(^|[[:space:]])--root([=[:space:]]|$)' <<<"${HELP_TEXT}"; then
  ARGS+=("--root" "${ROOT_DIR}")
elif grep -qE '(^|[[:space:]])--project-root([=[:space:]]|$)' <<<"${HELP_TEXT}"; then
  ARGS+=("--project-root" "${ROOT_DIR}")
fi

if grep -qE '(^|[[:space:]])--qa([=[:space:]]|$)' <<<"${HELP_TEXT}"; then
  ARGS+=("--qa")
elif grep -qE '(^|[[:space:]])--mode([=[:space:]]|$)' <<<"${HELP_TEXT}"; then
  ARGS+=("--mode" "qa")
fi

if grep -qE '(^|[[:space:]])--report-dir([=[:space:]]|$)' <<<"${HELP_TEXT}"; then
  ARGS+=("--report-dir" "${ROOT_DIR}/outputs/qa")
elif grep -qE '(^|[[:space:]])--report-path([=[:space:]]|$)' <<<"${HELP_TEXT}"; then
  ARGS+=("--report-path" "${ROOT_DIR}/outputs/qa")
fi

if grep -qE '(^|[[:space:]])--fail-on-warnings([=[:space:]]|$)' <<<"${HELP_TEXT}"; then
  ARGS+=("--fail-on-warnings")
elif grep -qE '(^|[[:space:]])--strict([=[:space:]]|$)' <<<"${HELP_TEXT}"; then
  ARGS+=("--strict")
fi

export PYTHONUNBUFFERED=1
cd "${ROOT_DIR}"

exec "${PYTHON_BIN}" "${CANONICALIZE_PY}" "${ARGS[@]}" "$@"
