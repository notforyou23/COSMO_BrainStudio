#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${ROOT_DIR}"

OUT_DIR="${ROOT_DIR}/outputs/qa"
mkdir -p "${OUT_DIR}"

SCHEMA="${ROOT_DIR}/schemas/METADATA_SCHEMA.json"
VALIDATOR="${ROOT_DIR}/scripts/qa/schema_validate.py"
JSON_OUT="${OUT_DIR}/schema_validation.json"
MD_OUT="${OUT_DIR}/schema_validation.md"

if [[ ! -f "${SCHEMA}" ]]; then
  echo "ERROR: Missing schema: ${SCHEMA}" >&2
  exit 2
fi

if [[ ! -f "${VALIDATOR}" ]]; then
  echo "ERROR: Missing validator: ${VALIDATOR}" >&2
  exit 2
fi

python3 "${VALIDATOR}" \
  --schema "${SCHEMA}" \
  --root "${ROOT_DIR}" \
  --json-out "${JSON_OUT}" \
  --md-out "${MD_OUT}"

echo "OK: schema validation complete"
echo "ARTIFACT: ${JSON_OUT}"
echo "ARTIFACT: ${MD_OUT}"
