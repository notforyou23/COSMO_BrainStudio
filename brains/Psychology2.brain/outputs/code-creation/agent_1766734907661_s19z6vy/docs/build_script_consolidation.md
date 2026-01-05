# Build script consolidation (runner + verifier)

This repo may contain multiple copies of `build_runner.py` and `verify_artifacts.py` produced by agent runs or forks. Consolidation selects one “best” pair, normalizes them to a single invariant build directory, and installs them into stable locations for repeatable usage.

## Goals and invariants

**Primary invariant:** all build outputs, logs, and reports must be written under:

- `runtime/_build/` (repo-relative)

Regardless of:
- current working directory when invoked
- the location of the selected candidate scripts
- whether the scripts are run via `python scripts/build_runner.py` or imported

The canonical runner/verifier must also:
- avoid writing to agent output directories
- use repo-relative path resolution (anchored at repo root)
- persist raw tool outputs plus a summarized report during verification

## Canonical locations (installed targets)

Consolidation installs exactly one canonical pair:

- `scripts/build_runner.py` (canonical runner)
- `scripts/verify_artifacts.py` (canonical verifier)
- `scripts/_build_common.py` (shared utilities)

The canonical pair is what CI/dev workflows should call. Any other duplicates are treated as candidates only.

## What the consolidator scans

`tools/consolidate_build_scripts.py` scans configured agent output roots (for example, agent run directories under `runtime/outputs/` or similar) looking for filename matches:

- `build_runner.py`
- `verify_artifacts.py`

Each discovered file becomes a candidate with metadata:
- absolute path
- repo-relative path (if inside repo)
- last modified time
- content (for heuristics)
- whether it appears to already use `runtime/_build/`

Candidates are paired by proximity (same directory preferred), but runner/verifier may be chosen independently if necessary.

## Candidate scoring and selection (heuristics)

Candidates are scored via lightweight static heuristics (no execution). Typical signals:

Positive signals:
- References `runtime/_build/` or a build-dir function that resolves to it
- Uses `pathlib.Path` and repo-root discovery
- Captures subprocess stdout/stderr to files
- Produces a machine-readable report (JSON) and a human summary (Markdown/text)
- Has a clear CLI entrypoint (`main()`, `if __name__ == "__main__":`)
- Avoids hard-coded absolute paths (user home, `/tmp`, etc.)
- Explicitly sets `cwd` for subprocesses or documents working-directory invariance

Negative signals:
- Writes outputs into the candidate’s own directory, CWD, or agent output folders
- Uses fragile relative paths without repo-root anchoring
- Mutates sys.path in unsafe ways
- Depends on non-standard environment variables without fallback
- Missing verifier outputs (no raw logs / no summarized report)

Tie-breakers:
1) Higher score wins
2) Prefer a matched pair from the same directory
3) Newer mtime wins if scores are equal
4) Shorter, clearer code may be preferred if functionally equivalent

The selected “best” runner and verifier become the input templates for canonicalization.

## Canonicalization: normalizing paths and imports

After selection, the consolidator rewrites/normalizes the scripts so that:

- Build root is resolved as: `<repo_root>/runtime/_build/`
- All artifact paths are derived from that build root (e.g., `artifacts/`, `logs/`, `reports/`)
- Logs and tool outputs are always stored under `runtime/_build/` and never elsewhere
- Imports are adjusted to use `scripts/_build_common.py` for shared behaviors:
  - repo root discovery
  - build dir resolution
  - subprocess execution wrappers
  - structured logging
  - report persistence

Any previous references like `runtime/build`, `./_build`, `./build`, `outputs/`, or agent-specific folders are replaced to honor the invariant.

## Runner behavior (canonical expectations)

`scripts/build_runner.py` should:
- create required subdirectories under `runtime/_build/`
- run the standardized build workflow
- write:
  - command logs (stdout/stderr) to `runtime/_build/logs/`
  - produced artifacts to `runtime/_build/artifacts/` (or a documented subfolder)
  - an execution summary (timings, commands, exit codes) to `runtime/_build/reports/`

If the build generates artifacts elsewhere, the runner should copy/sync them into `runtime/_build/artifacts/` so downstream verification always reads a single location.

## Verification behavior (canonical expectations)

`scripts/verify_artifacts.py` should:
- read current artifacts from `runtime/_build/` (not from CWD)
- run required validation tools (linters, schema checkers, packaging checks, etc.)
- persist:
  - raw outputs per tool/command under `runtime/_build/logs/verify/`
  - a summarized report under `runtime/_build/reports/verify_report.json` (and optionally `.md`)

The verifier should exit non-zero if required checks fail, while still writing logs and reports.

## Operational notes

- The consolidator is deterministic given identical inputs (same files, mtimes, scoring rules).
- The canonical scripts are safe to invoke from any directory because they compute repo root and use `runtime/_build/`.
- Downstream tooling should only depend on the canonical scripts and the `runtime/_build/` invariant, not on agent output layouts.
