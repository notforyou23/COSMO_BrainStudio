#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_ROOT="${LOG_ROOT:-$ROOT/runtime/_build/logs}"
TS="$(date -u +"%Y%m%dT%H%M%SZ")"
RUN_ID="${RUN_ID:-smoke_${TS}}"
IMAGE_NAME="${IMAGE_NAME:-generated_script_smoke:${TS}}"
DOCKERFILE_PATH="${DOCKERFILE_PATH:-$ROOT/Dockerfile}"

CPUS="${CPUS:-2}"
MEMORY="${MEMORY:-4g}"
SHM_SIZE="${SHM_SIZE:-1g}"
STOP_TIMEOUT="${STOP_TIMEOUT:-30}"
TIMEOUT_SECS="${TIMEOUT_SECS:-1200}"

WORKDIR="${WORKDIR:-/workspace}"
SMOKE_CMD="${SMOKE_CMD:-python -m pytest -q}"

mkdir -p "$LOG_ROOT"
BUILD_LOG="$LOG_ROOT/${RUN_ID}_docker_build.log"
RUN_LOG="$LOG_ROOT/${RUN_ID}_docker_run.log"
DOCKER_INFO_LOG="$LOG_ROOT/${RUN_ID}_docker_info.log"
INSPECT_LOG="$LOG_ROOT/${RUN_ID}_docker_inspect.json"
CONTAINER_LOG="$LOG_ROOT/${RUN_ID}_container.log"

CTR_NAME="${CTR_NAME:-${RUN_ID}}"

cleanup() {
  if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "$CTR_NAME"; then
    docker rm -f "$CTR_NAME" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

{
  echo "ts=$TS"
  echo "root=$ROOT"
  echo "run_id=$RUN_ID"
  echo "image=$IMAGE_NAME"
  echo "dockerfile=$DOCKERFILE_PATH"
  echo "cpus=$CPUS memory=$MEMORY shm=$SHM_SIZE timeout_secs=$TIMEOUT_SECS stop_timeout=$STOP_TIMEOUT"
  echo "workdir=$WORKDIR"
  echo "smoke_cmd=$SMOKE_CMD"
  echo "host_uname=$(uname -a || true)"
  echo "pwd=$(pwd)"
  echo "--- docker version ---"
  docker version || true
  echo "--- docker info ---"
  docker info || true
} >"$DOCKER_INFO_LOG" 2>&1

if [[ ! -f "$DOCKERFILE_PATH" ]]; then
  echo "ERROR: Dockerfile not found at: $DOCKERFILE_PATH" | tee -a "$DOCKER_INFO_LOG" >&2
  exit 2
fi

echo "Building image: $IMAGE_NAME"
(
  set -x
  docker build --progress=plain -f "$DOCKERFILE_PATH" -t "$IMAGE_NAME" "$ROOT"
) >"$BUILD_LOG" 2>&1 || {
  echo "ERROR: docker build failed. See: $BUILD_LOG" >&2
  exit 3
}

echo "Running smoke test container: $CTR_NAME"
python3 - <<PY >"$RUN_LOG" 2>&1
import os, shlex, subprocess, time, sys, json

root = os.environ.get("ROOT", "$ROOT")
name = os.environ.get("CTR_NAME", "$CTR_NAME")
image = os.environ.get("IMAGE_NAME", "$IMAGE_NAME")
workdir = os.environ.get("WORKDIR", "$WORKDIR")
cpus = os.environ.get("CPUS", "$CPUS")
memory = os.environ.get("MEMORY", "$MEMORY")
shm = os.environ.get("SHM_SIZE", "$SHM_SIZE")
stop_timeout = os.environ.get("STOP_TIMEOUT", "$STOP_TIMEOUT")
timeout_secs = int(os.environ.get("TIMEOUT_SECS", "$TIMEOUT_SECS"))
smoke_cmd = os.environ.get("SMOKE_CMD", "$SMOKE_CMD")

cmd = [
  "docker","run","--rm","--name",name,
  "--cpus",str(cpus),
  "--memory",str(memory),
  "--shm-size",str(shm),
  "--stop-timeout",str(stop_timeout),
  "-e","CI=1",
  "-e","PYTHONUNBUFFERED=1",
  "-v",f"{root}:{workdir}",
  "-w",workdir,
  image,
  "bash","-lc", smoke_cmd
]

print("CMD:", " ".join(shlex.quote(c) for c in cmd), flush=True)
t0 = time.time()
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

lines = []
try:
  for line in iter(p.stdout.readline, ""):
    if not line:
      break
    sys.stdout.write(line)
    lines.append(line)
    if time.time() - t0 > timeout_secs:
      raise TimeoutError(f"Timeout after {timeout_secs}s")
  rc = p.wait(timeout=max(1, timeout_secs - int(time.time()-t0)))
except TimeoutError as e:
  print(f"ERROR: {e}", flush=True)
  try:
    subprocess.run(["docker","stop","-t",str(stop_timeout),name], check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
  except Exception:
    pass
  rc = 124
except Exception as e:
  print(f"ERROR: runner exception: {e!r}", flush=True)
  try:
    subprocess.run(["docker","stop","-t",str(stop_timeout),name], check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
  except Exception:
    pass
  rc = 125

print(f"EXIT_CODE: {rc}", flush=True)
sys.exit(rc)
PY
RC=$?

if [[ $RC -ne 0 ]]; then
  echo "Smoke test failed (rc=$RC). Collecting diagnostics..." >&2
  docker logs "$CTR_NAME" >"$CONTAINER_LOG" 2>&1 || true
  docker inspect "$CTR_NAME" >"$INSPECT_LOG" 2>/dev/null || true
  echo "Logs:" >&2
  echo "  docker info:    $DOCKER_INFO_LOG" >&2
  echo "  build:          $BUILD_LOG" >&2
  echo "  run:            $RUN_LOG" >&2
  echo "  container logs: $CONTAINER_LOG" >&2
  echo "  inspect:        $INSPECT_LOG" >&2
  exit $RC
fi

echo "Smoke test succeeded."
echo "Logs:"
echo "  docker info: $DOCKER_INFO_LOG"
echo "  build:       $BUILD_LOG"
echo "  run:         $RUN_LOG"
