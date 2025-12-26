## `scripts/run_golden_path.sh` (single script) + one baseline run

The mission is to create **one** script (example path: `scripts/run_golden_path.sh`) that:

1. **Captures environment info** from the current execution context (notably: we have filesystem access under `/mnt/data` per the 2025‑12‑22 introspection note).
2. **Logs all steps** into `outputs/logs/`.
3. **Runs once** to generate a **baseline failure report** that can drive a minimal patch set.

This aligns with the accumulated guidance that computational work should be organized as **small, concrete, reproducible experiments** starting from a pinned repo/env state and producing a consistent output structure under `outputs/…` for validation, and that reproducibility is strengthened by deterministic pipelines with clear CLIs and golden tests.

---

# 1) Script: `scripts/run_golden_path.sh`

Create the file below exactly at `scripts/run_golden_path.sh`.

```bash
#!/usr/bin/env bash
set -euo pipefail

# Golden path runner:
# - captures environment + repo state
# - logs all steps to outputs/logs/
# - attempts a minimal "golden path" run and records failures to drive patching
#
# Context grounding:
# - We have filesystem access to /mnt/data (OpenAI code interpreter environment).
# - There exists a golden expected output file:
#     outputs/expected/benchmark_case_001.expected.json
#   referenced as a "Golden expected benchmark output used by tests"
#   (2025-12-22T18-56-46-314Z introspection note).

ROOT="${ROOT:-$(pwd)}"
TS="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
LOG_DIR="${ROOT}/outputs/logs"
RUN_DIR="${LOG_DIR}/${TS}"
LOG_FILE="${RUN_DIR}/run.log"
FAIL_FILE="${RUN_DIR}/baseline_failure_report.txt"
ENV_FILE="${RUN_DIR}/environment.txt"
TREE_FILE="${RUN_DIR}/repo_tree.txt"
PYPROJ_FILE="${RUN_DIR}/pyproject.toml.snapshot"
REQS_FILE="${RUN_DIR}/requirements.txt.snapshot"
EXPECTED_FILE_PATH="${ROOT}/outputs/expected/benchmark_case_001.expected.json"
EXPECTED_SNAPSHOT="${RUN_DIR}/benchmark_case_001.expected.json.snapshot"

mkdir -p "${RUN_DIR}"

# Send stdout+stderr to log, while still printing to terminal.
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "=== GOLDEN PATH RUN ==="
echo "timestamp_utc=${TS}"
echo "root=${ROOT}"
echo "run_dir=${RUN_DIR}"
echo

step() { echo; echo "---- STEP: $* ----"; }
note() { echo "NOTE: $*"; }

# Helper: run a command, capture status, and append failure details.
run_cmd() {
  local title="$1"; shift
  step "${title}"
  echo "+ $*"
  set +e
  "$@"
  local rc=$?
  set -e
  echo "exit_code=${rc}"
  if [[ "${rc}" -ne 0 ]]; then
    {
      echo "FAIL: ${title}"
      echo "CMD: $*"
      echo "EXIT_CODE: ${rc}"
      echo
    } >> "${FAIL_FILE}"
  fi
  return "${rc}"
}

# Helper: check for file existence; if missing, record in baseline failure report.
require_file() {
  local path="$1"
  step "Check required file exists: ${path}"
  if [[ -f "${path}" ]]; then
    echo "present=true"
    echo "path=${path}"
    echo "bytes=$(wc -c < "${path}" | tr -d ' ')"
  else
    echo "present=false"
    echo "path=${path}"
    {
      echo "FAIL: missing required file"
      echo "PATH: ${path}"
      echo
    } >> "${FAIL_FILE}"
    return 1
  fi
}

# Helper: snapshot a file if it exists
snapshot_file() {
  local src="$1"
  local dst="$2"
  step "Snapshot file: ${src} -> ${dst}"
  if [[ -f "${src}" ]]; then
    cp -f "${src}" "${dst}"
    echo "snapshotted=true"
  else
    echo "snapshotted=false (source missing)"
    {
      echo "FAIL: snapshot source missing"
      echo "SRC: ${src}"
      echo
    } >> "${FAIL_FILE}"
    return 1
  fi
}

# Start baseline report file with header
{
  echo "BASELINE FAILURE REPORT"
  echo "timestamp_utc=${TS}"
  echo "root=${ROOT}"
  echo
} > "${FAIL_FILE}"

# 1) Capture environment information (grounded: /mnt/data filesystem note)
step "Capture environment information"
{
  echo "ENVIRONMENT CAPTURE"
  echo "timestamp_utc=${TS}"
  echo "pwd=$(pwd)"
  echo "whoami=$(whoami || true)"
  echo
  echo "PATH=${PATH}"
  echo
  echo "Filesystem note: OpenAI code interpreter environment provides filesystem access to /mnt/data (per 2025-12-22 introspection)."
  echo "ls -la /mnt/data (if present):"
  ls -la /mnt/data 2>/dev/null || echo "(no /mnt/data visible)"
  echo
  echo "python --version:"
  python --version 2>&1 || echo "(python not available)"
  echo
  echo "python -c 'import sys; print(sys.executable); print(sys.version)':"
  python -c "import sys; print(sys.executable); print(sys.version)" 2>&1 || true
} | tee "${ENV_FILE}"

# 2) Capture repository state (tree + key dependency pins if present)
run_cmd "Capture repo tree (limited)" bash -lc "ls -la && (find . -maxdepth 4 -type f | sed 's|^\./||' | sort | head -n 400) > '${TREE_FILE}' && echo 'wrote: ${TREE_FILE}'"

# Snapshot known dependency manifests if they exist.
if [[ -f "${ROOT}/pyproject.toml" ]]; then
  snapshot_file "${ROOT}/pyproject.toml" "${PYPROJ_FILE}" || true
else
  note "pyproject.toml not found at repo root; continuing."
fi

if [[ -f "${ROOT}/requirements.txt" ]]; then
  snapshot_file "${ROOT}/requirements.txt" "${REQS_FILE}" || true
else
  note "requirements.txt not found at repo root; continuing."
fi

# 3) Ensure output scaffolding exists (grounded in reproducibility guidance)
step "Ensure output scaffolding exists"
mkdir -p "${ROOT}/outputs"
mkdir -p "${ROOT}/outputs/logs"
mkdir -p "${ROOT}/outputs/benchmark-repo" || true
mkdir -p "${ROOT}/outputs/expected" || true
echo "created_or_verified=outputs/, outputs/logs/, outputs/benchmark-repo/, outputs/expected/"

# 4) Verify the known golden expected output exists and snapshot it
#    (grounded in introspection item: outputs/expected/benchmark_case_001.expected.json)
require_file "${EXPECTED_FILE_PATH}" || true
if [[ -f "${EXPECTED_FILE_PATH}" ]]; then
  snapshot_file "${EXPECTED_FILE_PATH}" "${EXPECTED_SNAPSHOT}" || true
fi

# 5) Attempt to run known entrypoints (we only know about src/main.py and src/cli.py from memory)
#    We do not assume their CLI args; we run them in a way that produces failure logs if incorrect.
#
# From memory:
# - A project exists with src/main.py (size ~9781 bytes) and package src/sf_gft_diagnostics/*
# - Another project includes src/cli.py + src/lib/*
#
# We try:
# - python -m src.main (may fail; recorded)
# - python src/main.py (may fail; recorded)
# - python src/cli.py --help (help often succeeds if argparse/typer; if it fails, recorded)
#
# These attempts produce baseline failure report entries that drive minimal patching.

if [[ -f "${ROOT}/src/main.py" ]]; then
  run_cmd "Attempt run: python src/main.py" python "${ROOT}/src/main.py" || true
else
  {
    echo "FAIL: missing expected entrypoint"
    echo "PATH: src/main.py"
    echo
  } >> "${FAIL_FILE}"
fi

if [[ -f "${ROOT}/src/cli.py" ]]; then
  run_cmd "Attempt run: python src/cli.py --help" python "${ROOT}/src/cli.py" --help || true
else
  note "src/cli.py not found; skipping."
fi

# 6) If tests exist, try running them (without assuming pytest is installed; still informative)
# This is purely to generate actionable failure output.
run_cmd "Attempt run: pytest -q" bash -lc "pytest -q" || true

# 7) Summarize run artifacts
step "Summarize artifacts"
echo "log_file=${LOG_FILE}"
echo "baseline_failure_report=${FAIL_FILE}"
echo "environment_snapshot=${ENV_FILE}"
echo "repo_tree_snapshot=${TREE_FILE}"
[[ -f "${PYPROJ_FILE}" ]] && echo "pyproject_snapshot=${PYPROJ_FILE}"