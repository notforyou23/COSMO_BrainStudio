#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  echo "ERROR: python3 not found (set PYTHON_BIN to override)" >&2
  exit 127
fi

REPORT_PATH="${REPORT_PATH:-DRAFT_REPORT_v0.md}"
OUT_JSON="${OUT_JSON:-QA_REPORT.json}"
OUT_MD="${OUT_MD:-QA_REPORT.md}"

if [[ ! -f "${REPORT_PATH}" ]]; then
  echo "ERROR: Report not found: ${REPORT_PATH}" >&2
  echo "Remediation: place DRAFT_REPORT_v0.md at project root or set REPORT_PATH=/path/to/report.md" >&2
  exit 2
fi

run_cli() {
  "${PYTHON_BIN}" -m qa.run --report "${REPORT_PATH}" --out-json "${OUT_JSON}" --out-md "${OUT_MD}" "$@"
}

if run_cli "$@"; then
  :
else
  if [[ -f "qa/run.py" ]]; then
    "${PYTHON_BIN}" "qa/run.py" --report "${REPORT_PATH}" --out-json "${OUT_JSON}" --out-md "${OUT_MD}" "$@"
  else
    echo "ERROR: QA runner not found (qa.run module or qa/run.py missing)" >&2
    echo "Remediation: ensure qa/run.py exists and is importable as module qa.run" >&2
    exit 3
  fi
fi

if [[ ! -f "${OUT_JSON}" || ! -f "${OUT_MD}" ]]; then
  echo "ERROR: Expected outputs not created: ${OUT_JSON} and/or ${OUT_MD}" >&2
  echo "Remediation: check stderr above; ensure qa.run writes both outputs and you have write permission in ${PROJECT_ROOT}" >&2
  exit 4
fi

echo "WROTE:${OUT_JSON}"
echo "WROTE:${OUT_MD}"
