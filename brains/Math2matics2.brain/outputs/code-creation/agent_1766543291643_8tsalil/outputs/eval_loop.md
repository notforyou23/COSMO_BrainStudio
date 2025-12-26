# Evaluation loop (cycle procedure)

This document defines the *required* artifacts and the standard procedure for each evaluation cycle.

## Goal

Every cycle must produce reproducible evidence of what was run and what was tested. To enforce this, the project exposes `make run` and `make test` (or equivalent) targets that **always** write log files into `outputs/` on each invocation.

## Mandatory cycle artifacts (required every cycle)

A cycle is considered **invalid** unless *all* of the following exist after the cycle completes:

- `outputs/run.log` — complete stdout/stderr for the project run command.
- `outputs/test.log` — complete stdout/stderr for the project test command.

Notes:
- “Mandatory” means the files must be created/overwritten on **every** cycle (no reusing old logs).
- Logs must capture **all output** (stdout + stderr), and must be written even if the command fails.

## Standard cycle steps

1. **Clean/prepare output directory (optional)**
   - Ensure `outputs/` exists.
   - (Optional) delete prior logs if you want a clean diff; the make targets should overwrite anyway.

2. **Run**
   - Execute:
     - `make run`
   - Expected result:
     - `outputs/run.log` exists and contains the full console output from the run.

3. **Test**
   - Execute:
     - `make test`
   - Expected result:
     - `outputs/test.log` exists and contains the full console output from the test run.

4. **Validate artifacts**
   - Confirm both files exist:
     - `outputs/run.log`
     - `outputs/test.log`
   - If either is missing, rerun the corresponding target; do not proceed to reporting without both logs.

## Recommended Makefile behavior (contract)

Your build targets should follow this contract:

- `make run`:
  - runs the project (e.g., `python -m ...`, `python script.py`, etc.)
  - tees output into `outputs/run.log` while still printing to the terminal
  - captures stderr as well (e.g., `2>&1 | tee outputs/run.log`)
  - returns the underlying command’s exit code (fail the target if the run fails)

- `make test`:
  - runs the test command (e.g., `pytest`, `python -m unittest`, etc.)
  - tees output into `outputs/test.log` with stderr included
  - returns the underlying command’s exit code

This repo’s evaluation harness expects these two log files to be present after every cycle.
