# next — Mathematics coverage artifacts

This project provides a small, deterministic CLI that generates two artifacts for the **Mathematics** domain in `/outputs/`:

1. `coverage_matrix.csv` — machine-readable matrix of domains × subtopics × artifact types, with status and cross-link fields.
2. `eval_loop.md` — a human-readable 5-cycle evaluation cadence with metrics and decision rules for what to create next.

The outputs are designed to be versioned, diffed, and consumed by downstream agents or tooling.

## Quickstart

### Requirements
- Python 3.10+ recommended.

### Run the CLI
From the repository root:

```bash
python -m src.math_coverage_cli --outdir outputs
```

Common options (exact flags may vary by implementation, see `--help`):

```bash
python -m src.math_coverage_cli --help
python -m src.math_coverage_cli --outdir outputs --format csv
python -m src.math_coverage_cli --outdir outputs --emit-markdown-table
```

The CLI is expected to be deterministic: given the same taxonomy and code, it writes the same outputs (stable ordering, normalized line endings).

## What gets produced in /outputs

After a successful run, you should see:

- `/outputs/coverage_matrix.csv`
  - One row per (domain, subtopic, artifact_type).
  - Typical columns:
    - `domain`, `subtopic`, `artifact_type`
    - `status` (e.g., `missing`, `planned`, `draft`, `complete`)
    - `cross_links` (delimited list of references/paths/ids)
    - `notes` (short free text; keep stable if you care about diffs)
  - Intended use: programmatic coverage checks (count uncovered cells, filter by status, etc.).

- `/outputs/eval_loop.md`
  - Describes a 5-cycle review cadence, metrics to track, and decision rules.
  - Intended use: human process policy for iterative expansion and quality control.

## Taxonomy overview (how the matrix is populated)

The matrix is generated from `src/math_taxonomy.py`, which should define:
- A **domain taxonomy** (top-level domains like Algebra, Calculus, etc.).
- For each domain, a list of **subtopics**.
- A fixed set of **artifact types** to track per subtopic (e.g., `explanation`, `examples`, `exercises`, `solutions`, `cheatsheet`, `reference`).
- Default values for `status` and `cross_links` placeholders.

The CLI combines these into a cartesian product:
`rows = domains × subtopics × artifact_types`, then renders to CSV (and optionally a markdown table).

## Extending the taxonomy safely (for stable diffs)

To add or modify coverage without breaking consumers:

1. **Prefer appending over reordering**
   - Keep existing domain/subtopic/artifact_type ordering stable.
   - Append new items at the end of lists to reduce diff noise.

2. **Use stable identifiers**
   - Use consistent spelling/casing for `domain`, `subtopic`, and `artifact_type`.
   - Avoid punctuation churn (e.g., switching between “Number Theory” and “Number-Theory”).

3. **Avoid deletions when possible**
   - If something is deprecated, keep it and mark its `status` accordingly (e.g., `deprecated`) rather than removing rows.

4. **Keep artifact types fixed**
   - Changing the global artifact type list changes the shape of the matrix.
   - If you must add a new artifact type, add it once globally and regenerate outputs; expect all subtopics to gain a new row.

5. **Cross-links should be parseable**
   - Store cross-links as a deterministic, delimited list (for example `;`-separated).
   - Use paths relative to repo root when linking to files (e.g., `docs/algebra/groups.md`).

6. **Determinism checks**
   - Ensure renderers sort rows consistently and normalize line endings to `\n`.
   - Write files atomically (write temp then replace) to avoid partial outputs.

## Typical workflow

1. Update `src/math_taxonomy.py` (add domains/subtopics or adjust defaults).
2. Run the CLI to regenerate `/outputs/coverage_matrix.csv` and `/outputs/eval_loop.md`.
3. Review diffs:
   - Are there new uncovered cells (`status=missing`)?
   - Are cross-links preserved and well-formed?
   - Did ordering remain stable?

## Consuming the artifacts

- CSV can be read by any tooling (Python, spreadsheets, CI checks).
- The evaluation loop document provides the cadence and decision rules that a reviewer or agent can follow to decide what to create next based on:
  - artifact counts by status
  - number of cross-links per subtopic
  - number of uncovered cells (missing/planned)

If you build additional automation, treat `/outputs/coverage_matrix.csv` as the source of truth for coverage state and `/outputs/eval_loop.md` as the human policy layer.
