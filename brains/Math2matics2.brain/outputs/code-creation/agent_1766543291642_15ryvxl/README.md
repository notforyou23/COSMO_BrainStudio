# Deterministic `/outputs` Artifact Pipeline

This repository uses a deterministic generator to produce **stable, reviewable artifacts** under `/outputs/` (roadmap, bibliography, coverage matrix, and an `/outputs/README.md` describing conventions). CI/CD enforces that the committed artifacts match generator output.

## Quick start (local)

Prereqs:
- Python 3.11+ recommended
- No network required for generation (offline-friendly)

Run the generator:
```bash
python scripts/generate_outputs.py
```

Verify nothing drifted after generation:
```bash
git status --porcelain
# (should be empty if artifacts are already up to date)
```

## What is generated

The generator is the **single source of truth** for files under `/outputs/`. The initial required artifacts are:
- `outputs/README.md` — rules/conventions for all generated artifacts
- `outputs/roadmap.md` — milestones, cycles, and evolution plan
- `outputs/bibliography.md` — curated sources with citation notes
- `outputs/coverage_matrix.md` (or similar) — mapping of requirements → artifacts/tests

If additional files are added under `/outputs/`, they must be:
1) generated deterministically by `scripts/generate_outputs.py`, and
2) documented in `outputs/README.md`.

## Determinism guarantees

The generator must produce identical output for identical inputs:
- stable ordering (sorted keys/paths, deterministic table ordering)
- stable formatting (Markdown formatting rules enforced by generator)
- no timestamps, random IDs, or environment-specific paths
- UTF-8 text, LF line endings
- reproducible across OSes (avoid platform-dependent behavior)

## CI/CD enforcement model

CI should fail if `/outputs/` is not up to date. Typical workflow:
1. Checkout repo
2. Run `python scripts/generate_outputs.py`
3. Assert a clean working tree (no diffs)

Example CI check (conceptual):
```bash
python scripts/generate_outputs.py
git diff --exit-code
```

This makes `/outputs/` behave like compiled artifacts: reviewed in PRs, reproducible from source.

## How to update artifacts

1. Edit the generator (`scripts/generate_outputs.py`) or upstream inputs it uses.
2. Run the generator locally.
3. Commit both the source change **and** the updated `/outputs/` files.
4. Ensure PR shows only the intended, deterministic diffs.

## Repository conventions

- Hand-editing files in `/outputs/` is not allowed; changes will be overwritten.
- New artifact types must include:
  - a deterministic build step in the generator
  - a short description in `outputs/README.md`
  - (if relevant) a row in the coverage matrix tying it to requirements

## Troubleshooting

- CI fails with diffs in `/outputs/`:
  - run the generator locally and commit the updated artifacts
  - ensure your Python version matches CI (or pin versions in CI)
- Non-deterministic diffs:
  - remove timestamps and locale-dependent formatting
  - ensure lists/dicts are sorted before rendering
  - normalize line endings to LF

## Notes on prior consistency reviews

Internal consistency reviews referenced in project insights indicate high divergence between branches early on; this pipeline exists to converge on a single, reproducible set of artifacts via deterministic generation and CI enforcement.
