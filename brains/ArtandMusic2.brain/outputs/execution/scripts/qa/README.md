# QA Diagnostic Mode (Docker)

This project includes a *diagnostic run mode* intended to reliably reproduce QA failures with maximal telemetry, then iteratively remediate common causes until a minimal test run completes and writes artifacts under `outputs/qa/logs/`.

## When to use
Use diagnostic mode when:
- `pytest`/QA runs fail intermittently or with little output
- Docker containers exit unexpectedly (OOM, timeouts, bad mounts)
- Test discovery is expensive and fails before running any tests

## How to run

From the repository root:

- Run a diagnostic QA attempt (writes a new timestamped run directory):
  - `python scripts/qa/diagnostic_run.py`

- Optional common knobs (exact flags may vary by implementation):
  - `--image <docker-image>`: QA image to run
  - `--timeout <seconds>`: container execution timeout
  - `--memory <bytes|m|g>`: Docker memory limit (e.g., `2g`)
  - `--cpus <float>`: Docker CPU limit
  - `--workdir <path>`: container working directory
  - `--mount <host>:<container>`: additional bind mount(s)
  - `--pytest-args "<args>"`: extra pytest args (quoted)
  - `--attempts <n>`: remediation iterations

If Docker is unavailable or not running, diagnostic mode should fail fast and still emit host-side telemetry and a clear reason.

## Output layout

Artifacts are written under:
- `outputs/qa/logs/<run_id>/`

Where `<run_id>` is typically a timestamp or unique token.

Expected artifacts (names may be prefixed by attempt number):
- `summary.json`: high-level outcome, selected remediations, final status
- `attempts.jsonl`: one JSON object per attempt (parameters, results)
- `host_telemetry.json`: CPU/memory/disk/ulimits/environment snapshot
- `docker_version.txt` / `docker_info.txt`: Docker client/daemon details
- `container_create.json`: create parameters used for the container
- `container_inspect_pre.json` / `container_inspect_post.json`: Docker inspect snapshots
- `container_events.jsonl`: lifecycle events (create/start/die/oom/kill, etc.)
- `exit.json`: exit code, signal, OOMKilled, duration, timeout status
- `stdout.log` / `stderr.log`: captured container output (streamed)
- `pytest_report.json` or `junit.xml` (if enabled): test results artifacts
- `workdir_listing_pre.txt` / `workdir_listing_post.txt`: mounted directory sanity checks (optional)

The diagnostic run is considered successful when *at least one minimal test* completes (even if the full suite still fails), and logs are present under `outputs/qa/logs/`.

## What “maximal telemetry” means

Diagnostic mode aims to capture:
- Host limits: CPU count, memory, disk free, open file limits, ulimits
- Docker constraints: memory/cpu limits applied, shm size, pids limit, ulimit overrides
- Container lifecycle: create/start/stop/die events, exit code, signals, OOMKilled
- Time behavior: wall-clock duration, timeout enforcement, last log timestamps
- Mount correctness: working directory bind mounts and visibility inside the container

## Remediation strategy (how adjustments are selected)

Diagnostic mode runs in attempts. Each attempt applies the current configuration, captures telemetry, and classifies failure signals to choose the next remediation. Typical heuristics:

1. Timeouts / hangs
- Signal: attempt hits timeout, no progress in logs, or container remains running
- Action: increase timeout; enable log streaming; add periodic process snapshots

2. OOM / memory pressure
- Signal: `OOMKilled=true`, exit 137, kernel OOM messages, abrupt stop
- Action: increase Docker `--memory` and/or `--shm-size`; reduce parallelism; run a minimal test selection

3. Bad mounts / wrong working directory
- Signal: repo not found in container, tests cannot import project, empty directory
- Action: ensure bind mount of repo root; set container working directory; verify with `ls`/listing artifacts

4. Excessive test discovery / import-time failures
- Signal: failure before any tests run; long collection time; import errors during collection
- Action: restrict to a minimal test target (single file/test); add `-q` and disable plugins if needed; limit `pytest` collection scope

5. Docker runtime / permissions issues
- Signal: daemon unreachable, permission denied, image pull failures
- Action: emit actionable error + environment details; do not loop endlessly; stop after clear non-remediable diagnosis

The chosen remediation steps (and the evidence that triggered them) are recorded in `summary.json` and per-attempt records.

## Reading results quickly

Start with:
1. `outputs/qa/logs/<run_id>/summary.json`
2. `exit.json` (exit code, OOMKilled, timeout)
3. `stdout.log` / `stderr.log`
4. `container_events.jsonl` (to confirm lifecycle and OOM/kill events)
5. `container_inspect_post.json` (state, mounts, resource limits)

## Minimal success definition

Diagnostic mode aims to get to:
- container starts successfully
- project directory is visible in container workdir
- `pytest` runs at least one test (or a minimal smoke check) and exits with a recorded code
- logs and telemetry are written under `outputs/qa/logs/<run_id>/`

Even if the full suite remains failing, this provides a stable baseline for debugging and CI hardening.
