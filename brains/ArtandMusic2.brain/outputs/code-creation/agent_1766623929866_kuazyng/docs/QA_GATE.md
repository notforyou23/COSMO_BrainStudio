# QA Gate: one-command delivery verification

This project provides a single “QA gate” command that deterministically generates required outputs and validates that the delivery artifacts exist and are minimally complete. The gate MUST be runnable locally and in CI and MUST exit nonzero on any failure.

## Canonical command (recommended)

Run from the repo root:

    python -m tools.pipeline

Behavior:
- Runs `init_outputs` then `validate_outputs` in a fixed order.
- Performs additional artifact checks (presence + minimal completeness).
- Prints a concise QA gate report and exits with:
  - `0` on success
  - nonzero on any failure (missing artifacts, malformed content, stage failure)

## Alternative wrapper (if present)

Some setups may also provide:

    scripts/run_pipeline.sh

This wrapper should call the canonical Python entrypoint and propagate the exit code.

## What the QA gate validates

The gate verifies that required deliverables exist at canonical paths and meet minimal heuristics (to prevent “empty file” compliance). Exact paths may be resolved via canonicalization helpers, but the intent is:

1) Tracking reconciliation
- `TRACKING_RECONCILIATION.md` exists.
- Non-trivial content (not empty/whitespace; should include at least a few lines/sections so it is reviewable).

2) Claim Cards
- A Claim Cards directory exists (commonly `claim_cards/` or similar).
- Contains at least one claim card file.
- Each card is non-trivial (not empty; includes identifying metadata such as a title/claim id and evidence links/notes).

3) QA gate artifacts
- A QA gate output directory exists (commonly `qa_gate/`).
- Contains gate outputs such as a report/summary (for example: `qa_gate_report.json`, `qa_gate_report.md`, or equivalent).
- Report is parseable (if JSON) and contains a pass/fail outcome and at least one check result.

In addition, `validate_outputs` is expected to run the project’s standard validations (schemas, lint-like checks, expected output inventory, etc.), and any failure is a gate failure.

## Local usage patterns

Run the gate:

    python -m tools.pipeline

To see a failing exit code:

    python -m tools.pipeline; echo $?

If you are iterating quickly, fix the first reported failure (missing file, empty content, invalid structure), then re-run.

## CI usage (example)

Use the canonical command as a dedicated job step; fail the build on nonzero exit:

GitHub Actions snippet:

    - name: QA gate
      run: python -m tools.pipeline

Tip: keep the QA gate in a separate step so failures are clearly attributable, and so artifacts (reports) can be uploaded on failure.

## Common failure modes and fixes

1) Missing `TRACKING_RECONCILIATION.md`
- Cause: pipeline didn’t generate it or it was written to a non-canonical location.
- Fix: ensure `init_outputs` writes it, or add/adjust canonical path handling so the gate can find it.

2) Tracking reconciliation is “present but empty”
- Cause: file exists but contains placeholder/boilerplate only.
- Fix: add real reconciliation content (sources, decisions, counts/notes, links).

3) No Claim Cards found
- Cause: directory name mismatch or cards not generated.
- Fix: ensure claim card generation runs in `init_outputs` and uses the expected directory; confirm at least one card exists.

4) Claim Cards exist but fail minimal completeness
- Cause: empty files or missing required fields/structure.
- Fix: include title/id, a clear claim statement, and evidence/links; avoid blank templates.

5) QA gate report missing or malformed
- Cause: gate orchestration didn’t write a report, or JSON is invalid.
- Fix: ensure the QA gate orchestration writes a deterministic report and that any JSON is valid/parseable.

6) Non-deterministic failures
- Cause: relying on timestamps/random order, environment-specific paths, or network access.
- Fix: make ordering explicit, canonicalize paths, avoid network dependence, and keep outputs deterministic.

## Design notes (expectations)

- The QA gate is the single source of truth for “ready to deliver”.
- It should be fast enough to run routinely and strict enough to prevent incomplete deliveries.
- All checks should have actionable error messages that point to the failing artifact and expected structure.
