# CI pipeline (deterministic artifacts)

This repository uses CI to ensure the end-to-end pipeline runs from a fresh checkout and produces a fixed set of deterministic artifacts under `./outputs/`.

## What CI does

On every push/PR, the CI job:
1. Checks out the repo (clean workspace).
2. Installs Python dependencies (clean environment).
3. Runs the pipeline: `python scripts/run_pipeline.py`.
4. Validates artifacts:
   - required files exist under `./outputs/`
   - their content is deterministic by checksum comparison to `outputs/golden_manifest.json`
5. Fails the job (and blocks merge) if any step fails.

The validation logic lives in `scripts/ci/validate_artifacts.py` and is invoked by the workflow (see `.github/workflows/pipeline-ci.yml`).

## Required artifacts

The canonical list of required artifacts and their checksums is tracked in:
- `outputs/golden_manifest.json`

The manifest is treated as the source of truth: every file listed must exist after the pipeline run, and its checksum must match the manifest. Any extra files under `outputs/` may be ignored unless they are in the manifest.

## Determinism enforcement

Determinism is enforced by hashing artifact contents and comparing them against the committed golden manifest. This catches:
- nondeterministic outputs (timestamps, random seeds, unordered dict/set iteration, locale/timezone differences)
- changes to exported formats
- accidental changes to pipeline logic

To keep builds deterministic:
- avoid embedding wall-clock timestamps or run IDs in output files
- fix random seeds where randomness is used
- ensure stable ordering when serializing collections (e.g., sort keys/rows)
- write normalized text (line endings, encoding) and stable numeric formatting

## Updating the golden manifest (intentional changes)

If you intentionally changed the pipeline outputs, update the golden manifest as part of the same PR:

1. Run locally from a clean state:
   - delete `outputs/` (or ensure it is empty)
   - run: `python scripts/run_pipeline.py`
2. Re-generate/update the manifest using the validator's "write manifest" mode (see `scripts/ci/validate_artifacts.py --help`), producing a new `outputs/golden_manifest.json`.
3. Inspect the diff:
   - verify only expected artifacts changed
   - verify no sensitive data is introduced into `outputs/`
4. Commit the updated `outputs/golden_manifest.json` and any intended artifact format changes.

PRs that modify outputs without updating the manifest will fail CI by design.

## Troubleshooting CI failures

Common failure modes:
- Missing required artifact: the pipeline did not produce a file listed in the manifest.
- Checksum mismatch: output changed or became nondeterministic.
- Dependency drift: upstream library version differences causing formatting changes.

Recommended debugging steps:
- run `python scripts/run_pipeline.py` locally
- run `python scripts/ci/validate_artifacts.py` to see which file differs
- compare the failing artifact with the expected version (diff/inspect)
- make output generation stable or update the golden manifest intentionally.
