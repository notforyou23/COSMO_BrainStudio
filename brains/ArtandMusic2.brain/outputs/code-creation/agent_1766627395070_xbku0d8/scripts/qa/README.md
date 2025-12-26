# QA runner (scripts/qa_run.sh / python -m qa.run)

This project provides a single-entry QA pipeline that:
1) generates/collects QA artifacts,
2) validates that required output paths exist,
3) writes a run summary to `outputs/qa/qa_summary.json` and `outputs/qa/qa_summary.md` (time, git SHA, inputs, checks).

## Quick start

From the repo root:

- Shell entrypoint:
  - `bash scripts/qa_run.sh`

- Python entrypoint:
  - `python -m qa.run`

If your environment uses an explicit interpreter:
- `python3 -m qa.run`

## Expected inputs

The runner is designed to be safe to run locally and in CI. Inputs are typically provided via:
- the current working tree (repo contents),
- environment variables and/or CLI flags (depending on implementation),
- any upstream artifacts already present in `outputs/` (if the pipeline supports collection/aggregation).

At minimum, ensure:
- you are in the repository root (so git metadata and relative paths resolve),
- Python can import the `qa` package (repo root on `PYTHONPATH` or installed package),
- the process can create/write to the `outputs/` directory.

## Produced outputs

Primary outputs (always written on a successful run):

- `outputs/qa/qa_summary.json`
  - machine-readable summary including:
    - `started_at` / `finished_at` timestamps (ISO 8601),
    - git SHA (if available),
    - resolved inputs and configuration used,
    - list of artifacts generated/collected,
    - required-path checks and their pass/fail status.

- `outputs/qa/qa_summary.md`
  - human-readable summary with the same essential metadata.

Typical secondary outputs (implementation-specific, may vary):
- generated/collected artifact files under `outputs/qa/` and/or other `outputs/*` locations,
- intermediate logs written by the pipeline steps.

## How validation works

The runner checks that required output paths exist after artifact generation/collection.
If any required path is missing, the run should:
- record failures in the summary files,
- exit non-zero (in CI this fails the job).

## Troubleshooting

### `python -m qa.run` fails with import errors
- Run from the repo root.
- Ensure the repo root is on `PYTHONPATH`, or install the package in your environment.
- Confirm `qa/run.py` exists and is importable.

### Git SHA is missing in the summary
- The runner typically reads git metadata via `git rev-parse HEAD`.
- Make sure `git` is installed and the working directory is a git repo.
- In CI, shallow clones may require fetching the commit; ensure the checkout step includes history as needed.

### Permission errors writing to `outputs/`
- Ensure the current user can create/write `outputs/qa/`.
- In CI/container contexts, verify the workspace is writable.

### Required outputs reported missing
- Check the pipeline logs (if emitted) for earlier step failures.
- Ensure upstream steps that generate those paths are enabled and configured.
- Confirm any input files/directories referenced by the pipeline exist.

## Notes for CI usage
- Prefer the single entrypoint (shell or python module) so the summary files are always emitted.
- Archive `outputs/qa/qa_summary.json` and `outputs/qa/qa_summary.md` as job artifacts for easy inspection.
