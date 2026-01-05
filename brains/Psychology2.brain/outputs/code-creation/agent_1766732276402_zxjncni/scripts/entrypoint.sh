#!/usr/bin/env bash
set -euo pipefail

umask 0022
export LC_ALL="${LC_ALL:-C.UTF-8}"
export LANG="${LANG:-C.UTF-8}"
export TZ="${TZ:-UTC}"

# Determinism and stability knobs
export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"
export PYTHONDONTWRITEBYTECODE="${PYTHONDONTWRITEBYTECODE:-1}"
export PYTHONHASHSEED="${PYTHONHASHSEED:-0}"
export PIP_DISABLE_PIP_VERSION_CHECK="${PIP_DISABLE_PIP_VERSION_CHECK:-1}"
export PIP_NO_CACHE_DIR="${PIP_NO_CACHE_DIR:-1}"
export PIP_DEFAULT_TIMEOUT="${PIP_DEFAULT_TIMEOUT:-60}"

log() { printf '%s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }
need_cmd() { command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"; }

need_cmd python
need_cmd pip

if [[ "${ENTRYPOINT_STRICT:-1}" == "1" ]]; then
  shopt -s inherit_errexit 2>/dev/null || true
fi

WORKDIR="${WORKDIR:-$(pwd)}"
cd "$WORKDIR"

log "Entrypoint starting in: $WORKDIR"
log "Python: $(python -V 2>&1)"
log "Pip: $(pip --version 2>&1 | tr -s ' ')"

if [[ -f "requirements.lock.txt" ]]; then
  log "Found requirements.lock.txt (pinned dependencies)."
else
  log "NOTE: requirements.lock.txt not found (continuing)."
fi

if [[ -f "environment.manifest.json" ]]; then
  log "Found environment.manifest.json (reproducibility manifest)."
else
  log "NOTE: environment.manifest.json not found (continuing)."
fi

# Smoke-test: verify interpreter, key stdlib, filesystem, and metadata collection.
python - <<'PY'
import json, os, platform, sys, subprocess, time
from pathlib import Path

def run(cmd):
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        return out.strip()
    except Exception as e:
        return f"<error:{e}>"

# Basic sanity
assert sys.version_info[:2] >= (3, 8), f"Python too old: {sys.version}"
import json as _json, hashlib, ssl, sqlite3, uuid  # stdlib availability

# Filesystem write check
p = Path(".smoke_test_write")
p.write_text("ok", encoding="utf-8")
assert p.read_text(encoding="utf-8") == "ok"
p.unlink(missing_ok=True)

runtime = {
    "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "python": {
        "executable": sys.executable,
        "version": sys.version.replace("\n", " "),
        "implementation": platform.python_implementation(),
    },
    "platform": {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "system": platform.system(),
        "release": platform.release(),
    },
    "pip": {
        "version": run([sys.executable, "-m", "pip", "--version"]),
        "freeze_head": run([sys.executable, "-m", "pip", "freeze", "--disable-pip-version-check"]).splitlines()[:50],
    },
    "env": {
        "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED"),
        "LC_ALL": os.environ.get("LC_ALL"),
        "LANG": os.environ.get("LANG"),
        "TZ": os.environ.get("TZ"),
    },
}

out_path = Path(os.environ.get("RUNTIME_ENV_JSON_PATH", "runtime.env.json"))
out_path.write_text(json.dumps(runtime, indent=2, sort_keys=True), encoding="utf-8")
print(f"SMOKE_TEST_OK: wrote {out_path}")
PY

export RUNTIME_ENV_JSON_PATH="${RUNTIME_ENV_JSON_PATH:-runtime.env.json}"
export ENV_MANIFEST_RUNTIME_PATH="$RUNTIME_ENV_JSON_PATH"

# Runner selection: allow override; otherwise try common locations.
RUNNER_CMD_DEFAULT=""
if [[ -f "runner.py" ]]; then
  RUNNER_CMD_DEFAULT="python -u runner.py"
elif [[ -f "scripts/runner.py" ]]; then
  RUNNER_CMD_DEFAULT="python -u scripts/runner.py"
elif [[ -f "scripts/run.py" ]]; then
  RUNNER_CMD_DEFAULT="python -u scripts/run.py"
fi

RUNNER_CMD="${RUNNER_CMD:-$RUNNER_CMD_DEFAULT}"
[[ -n "$RUNNER_CMD" ]] || die "Could not find runner. Set RUNNER_CMD to the command that launches the JSON-driven pipeline."

log "Launching runner: $RUNNER_CMD $*"
exec bash -lc "$RUNNER_CMD \"$@\""
