# QA Gate (container + failsafe)

This folder defines the developer-facing contract for the project “QA gate” runner.

Goal:
- Provide one canonical entrypoint (`qa_gate.py`) that *tries containerized execution first* for full coverage.
- If Docker is unavailable or the container is lost, *automatically fall back* to a no-container “failsafe” mode that still produces logs and partial results (never “dies silently”).

## Canonical entrypoint

Preferred command (used by CI and locally):
- `python scripts/qa/qa_gate.py`

Behavior:
1) Container mode (primary): uses Docker to run the full QA command set in a clean, reproducible environment.
2) Failsafe mode (fallback): runs a reduced, deterministic subset locally with strict timeouts and structured error capture.

Failsafe is triggered when:
- Docker is missing / cannot be invoked
- Image/pull/run failures prevent starting the container
- Container-loss scenarios occur (runner cannot retrieve exit code/logs, daemon reset, abrupt termination)

## Outputs and artifacts

All modes must write artifacts under:
- `/outputs/qa/` (created by `artifacts.py`)

Artifacts are designed to answer:
- What ran? (metadata)
- Where are the logs? (stdout/stderr)
- What passed/failed? (partial results)
- Why did it fail / fall back? (error report + mode signal)

Expected artifact set (names may be stable across modes):
- `run.json`: machine-readable metadata (timestamps, mode, commands, versions, environment hints)
- `stdout.log`: captured standard output (container or local)
- `stderr.log`: captured standard error (container or local)
- `results.json`: structured summary (tests attempted, counts, failures, skipped, timeouts)
- `error.json` (optional): structured exception details when the runner fails or falls back
- `RUN_INSTRUCTIONS.md`: “how to rerun this exact gate” for humans (command + notes)

Notes:
- Container mode should attempt to capture *complete logs* even on failures.
- Failsafe mode must always emit *at least* metadata + logs + partial results, even if some tests crash or time out.

## Container mode (docker_runner.py)

Container mode is intended to be the authoritative, full QA gate:
- runs the full test/lint/typecheck suite
- uses a known image/toolchain
- produces deterministic results across machines

Implementation requirements:
- capture stdout/stderr to files in `/outputs/qa/`
- return an exit code that reflects the in-container command outcome
- detect “container lost” / daemon interruption conditions and report them clearly (so `qa_gate.py` can fall back)

## Failsafe mode (failsafe_runner.py)

Failsafe mode is a “degraded but safe” execution path:
- no Docker required
- reduced test set chosen to be fast and deterministic
- strict per-step timeouts to prevent hangs
- errors are captured and serialized (no silent termination)

Typical failsafe steps (project-defined):
- a minimal lint/static check subset
- a minimal unit test subset (or a small curated list)
- a smoke import/runtime check

Non-goals:
- achieving full parity with container mode
- relying on network access or heavy, flaky integration tests

## Extending / customizing test sets

The QA gate supports two test sets:
- Full suite (container mode): prioritize completeness and reproducibility.
- Reduced suite (failsafe mode): prioritize determinism, low resource usage, and bounded runtime.

Guidelines:
- Prefer adding new checks to container mode first.
- Add to failsafe only if it is:
  - fast (<~minutes, not tens of minutes)
  - deterministic (no network, no external services, no large downloads)
  - robust on developer laptops and limited CI runners

When adding a new check:
1) Define the command and expected timeout.
2) Ensure stdout/stderr are captured.
3) Ensure failures are recorded in `results.json` with a clear label.
4) Ensure the gate still writes artifacts even when the new check crashes.

## Reading outcomes

Success:
- container mode completes; `results.json` indicates all required checks passed.

Soft degradation:
- container mode fails to start or is lost; `run.json` indicates `mode: failsafe` (and includes why).
- failsafe results determine overall exit code (project policy), but artifacts always exist.

Hard failure:
- both container and failsafe cannot execute; `error.json` must explain why and logs must exist.

## Quick rerun instructions

After any gate run, consult:
- `/outputs/qa/RUN_INSTRUCTIONS.md`

It should contain the exact command to rerun the last gate and notes about whether it used container or failsafe mode.
