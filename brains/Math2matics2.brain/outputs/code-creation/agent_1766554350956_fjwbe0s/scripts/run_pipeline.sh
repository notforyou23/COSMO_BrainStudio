#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUT_DIR="${ROOT_DIR}/outputs"
mkdir -p "${OUT_DIR}"

SEED_DEFAULT="1337"
SEED="${PIPELINE_SEED:-${SEED_DEFAULT}}"
ARGS=()

usage() {
  cat <<'USAGE'
Usage: scripts/run_pipeline.sh [--seed N] [--outputs DIR] [--] [extra python args...]

Runs the pipeline deterministically and writes artifacts under ./outputs by default.

Environment variables:
  PIPELINE_SEED   Seed to use (overrides default 1337)
  PYTHON          Python executable to use (default: python)
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --seed)
      shift
      [[ $# -gt 0 ]] || { echo "ERROR: --seed requires a value" >&2; exit 2; }
      SEED="$1"
      shift
      ;;
    --seed=*)
      SEED="${1#*=}"
      shift
      ;;
    --outputs)
      shift
      [[ $# -gt 0 ]] || { echo "ERROR: --outputs requires a value" >&2; exit 2; }
      OUT_DIR="$(python - <<PY
import os,sys
p=sys.argv[1]
print(os.path.abspath(p))
PY
"$1")"
      shift
      mkdir -p "${OUT_DIR}"
      ;;
    --outputs=*)
      OUT_DIR="$(python - <<PY
import os,sys
p=sys.argv[1]
print(os.path.abspath(p))
PY
"${1#*=}")"
      shift
      mkdir -p "${OUT_DIR}"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      while [[ $# -gt 0 ]]; do ARGS+=("$1"); shift; done
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done

export PYTHONHASHSEED="${SEED}"
export PIPELINE_SEED="${SEED}"
export PIPELINE_OUTPUTS_DIR="${OUT_DIR}"
export PYTHONIOENCODING="utf-8"
export PYTHONUTF8="1"

LOG_FILE="${OUT_DIR}/run.log"
: > "${LOG_FILE}"
exec > >(tee -a "${LOG_FILE}") 2>&1

PY="${PYTHON:-python}"
cd "${ROOT_DIR}"

echo "ROOT_DIR=${ROOT_DIR}"
echo "OUT_DIR=${OUT_DIR}"
echo "SEED=${SEED}"
echo "PY=${PY}"
echo "CMD=${PY} -m pipeline.entrypoint --outputs \"${OUT_DIR}\" --seed \"${SEED}\" ${ARGS[*]:-}"

"${PY}" -m pipeline.entrypoint --outputs "${OUT_DIR}" --seed "${SEED}" "${ARGS[@]}
