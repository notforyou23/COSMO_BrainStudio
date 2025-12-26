# Smoke-test gate (Docker + CI)

This project includes a minimal “container health” smoke test that runs the smallest possible in-container command, captures full stdout/stderr + exit code, and writes a timestamped log bundle to a canonical output path (`/out` preferred, `/outputs` supported, with fallbacks).

The smoke test is intended to be the first CI gate before any longer or more expensive jobs run.
## What the smoke test does

Inside the container it will:
- Execute a minimal command (e.g., `sh -lc 'echo OK'` or similar smallest viable command).
- Capture: command, exit code, stdout, stderr, runtime info.
- Write a timestamped log bundle directory, for example:
  - `/out/smoke_test/2025-12-25T01-21-50Z_<id>/`
  - containing `stdout.txt`, `stderr.txt`, and a structured `meta.json` (names may vary slightly but always include stdout/stderr/exit code).

The bundle path is chosen by the scripts:
1) `/out` if writable (recommended for Docker mounts)
2) else `/outputs` if writable
3) else a safe fallback inside the container (used only when mounts are unavailable)
## Local run with Docker

### Prerequisites
- Docker Engine + Docker Compose v2 (`docker compose version`)

### Build the image
From the repo root:
- `docker build -t smoke-test:local .`

### Run the smoke test (recommended: persist logs on the host)
1) Create a host output directory:
- `mkdir -p outputs`

2) Run the container and mount `./outputs` to `/out`:
- `docker run --rm -v "$PWD/outputs:/out" smoke-test:local python scripts/smoke_test.py`

After the run, look under:
- `./outputs/smoke_test/<timestamped_bundle>/`

### Run via Compose (if docker-compose.yml is present)
- `mkdir -p outputs`
- `docker compose up --build --abort-on-container-exit --exit-code-from smoke_test`

Logs persist under `./outputs/` because it is mounted to `/out` in the container.
## Where outputs are written

Canonical in-container locations:
- Primary: `/out` (best for CI and local Docker because it is easy to mount)
- Secondary: `/outputs`

Host paths:
- Local Docker (examples above): `./outputs/` on your machine maps to `/out` in the container.

If neither `/out` nor `/outputs` are writable, the smoke test will still run and write to a fallback location; however, CI should mount `/out` so the log bundle is always persisted and retrievable.
## CI gate behavior

The smoke test should be the *first* step in CI:
- It must run quickly.
- It must fail fast if the container cannot start, cannot execute commands, or cannot write outputs.

A typical CI gate flow:
1) Build image.
2) Run smoke test container (mounted `/out` or `/outputs`).
3) Fail the pipeline if the container exit code is non-zero.
4) Upload the log bundle directory as a CI artifact (so stdout/stderr/meta are available even on failures).
5) Only then proceed to longer integration or workload runs.

Example (conceptual) gating rule:
- If `scripts/smoke_test.py` exits non-zero OR no bundle is written under `/out`, the job fails and subsequent jobs do not run.
## Troubleshooting

- No logs on host:
  - Ensure you mounted a host directory to `/out` (recommended), e.g. `-v "$PWD/outputs:/out"`.
- Permission errors writing `/out`:
  - Verify the host directory exists and is writable by Docker.
- Smoke test passes locally but fails in CI:
  - Check CI runner’s Docker permissions and that the artifact directory is mounted to `/out` and collected after the run.
