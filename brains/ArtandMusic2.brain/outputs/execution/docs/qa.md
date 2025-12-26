# QA (Canonical Runner + Artifacts)

This project defines **one canonical QA entry point** and **one canonical artifact location**.

## Canonical command (the only supported QA invocation)

Run QA from the repo root with:

    python scripts/qa_run.py

Notes:
- Do not run ad-hoc scripts that write to other output folders for QA evidence.
- The runner is responsible for producing a single, self-contained artifact tree under `/outputs/qa/` and then invoking `scripts/validate_outputs.py` on that tree.

## Canonical artifact location

All QA artifacts **MUST** be written under:

    /outputs/qa/<run_id>/

No QA workflow step is allowed to write evidence outside `/outputs/qa/<run_id>/` during a run.

### run_id

`<run_id>` is a unique identifier for the run (e.g., a timestamp-based ID). It is used as the folder name under `/outputs/qa/`.

## Required artifact tree

Each run MUST produce the following minimum structure:

    /outputs/qa/<run_id>/
      index.json
      manifest.jsonl
      validation/
        validate_outputs.json

### index.json (required)

A single, explicit index that points to all other evidence for the run.

Required fields:
- `run_id` (string)
- `created_at` (string, ISO-8601)
- `root` (string; should be `outputs/qa/<run_id>` or an equivalent repo-relative path)
- `artifacts` (object mapping logical names to repo-relative paths)
- `command` (string; the canonical invocation used)
- `status` (string; e.g., `passed` / `failed`)

`artifacts` MUST include at least:
- `manifest`: path to `manifest.jsonl`
- `validation_report`: path to `validation/validate_outputs.json`

### manifest.jsonl (required)

A line-delimited JSON manifest of produced files for the run.

Each line MUST describe exactly one file artifact and include:
- `path` (repo-relative path under `outputs/qa/<run_id>/`)
- `sha256` (hex string)
- `bytes` (int)
- `media_type` (string; e.g., `application/json`, `text/plain`, `text/markdown`, `image/png`)
- `created_at` (string, ISO-8601)

The manifest is the authoritative inventory; `index.json` is the human/machine entry point.

### validation/validate_outputs.json (required)

The output of running:

    python scripts/validate_outputs.py --root outputs/qa/<run_id>

It MUST be written inside the run folder at:

    outputs/qa/<run_id>/validation/validate_outputs.json

The canonical runner MUST fail the command (non-zero exit) if validation fails.

## What the canonical runner guarantees

`python scripts/qa_run.py` MUST:
1. Create a new run folder at `outputs/qa/<run_id>/`.
2. Execute the configured QA workflow, writing evidence only within that folder.
3. Write `manifest.jsonl` describing every file artifact produced.
4. Write `index.json` that references the manifest and all key artifacts.
5. Run `scripts/validate_outputs.py` against the run folder and write the validation report under `validation/`.
6. Exit non-zero if validation fails, leaving the artifacts intact for inspection.

## Supported evidence locations (strict)

Only these are supported for QA evidence and validation:
- `outputs/qa/<run_id>/...` (the canonical run folder)
- `outputs/qa/` (container folder holding multiple runs)

Anything else is non-canonical and may be ignored by automation and reviewers.
