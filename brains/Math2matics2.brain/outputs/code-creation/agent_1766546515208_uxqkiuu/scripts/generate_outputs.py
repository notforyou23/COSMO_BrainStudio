#!/usr/bin/env python3
"""Deterministically generate project outputs.

Creates:
- outputs/coverage_matrix.csv (stable ontology columns + seed rows)
- outputs/eval_loop.md (5-cycle cadence, metrics, thresholds, decision rules)

Usage:
  python scripts/generate_outputs.py
  python scripts/generate_outputs.py --outdir outputs
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from tempfile import NamedTemporaryFile
COVERAGE_COLUMNS = ["domain", "subtopic", "artifact_type", "status", "link"]

SEED_ROWS = [
    # domain, subtopic, artifact_type, status, link
    {"domain": "data", "subtopic": "ingestion", "artifact_type": "spec", "status": "planned", "link": ""},
    {"domain": "data", "subtopic": "schema", "artifact_type": "documentation", "status": "planned", "link": ""},
    {"domain": "modeling", "subtopic": "baseline", "artifact_type": "notebook", "status": "planned", "link": ""},
    {"domain": "evaluation", "subtopic": "offline_metrics", "artifact_type": "report", "status": "planned", "link": ""},
    {"domain": "deployment", "subtopic": "ci_cd", "artifact_type": "pipeline", "status": "planned", "link": ""},
    {"domain": "governance", "subtopic": "risk_and_compliance", "artifact_type": "checklist", "status": "planned", "link": ""},
]
EVAL_LOOP_MD = """# Evaluation loop (5-cycle cadence)

This document defines a lightweight evaluation loop to keep artifacts aligned and improve quality in a controlled, repeatable way.

## Cadence (5 cycles)

**Cycle 1 — Baseline & scope lock**
- Confirm goals, scope boundaries, and stable ontology (columns/definitions).
- Produce initial artifacts and a baseline measurement snapshot.

**Cycle 2 — Coverage expansion**
- Add/extend artifacts to increase coverage; keep schema stable.
- Re-run evaluations; track deltas against Cycle 1.

**Cycle 3 — Consistency & regression control**
- Focus on reducing inconsistencies across artifacts and preventing regressions.
- Add checks that fail fast when outputs drift unexpectedly.

**Cycle 4 — Quality tightening**
- Improve clarity, completeness, and adherence to decision rules.
- Raise the bar on thresholds if stable for 2 consecutive cycles.

**Cycle 5 — Release readiness**
- Freeze changes, confirm thresholds, and publish final artifacts.
- Document known gaps and a backlog for the next iteration.

## Required metrics

Track these metrics each cycle (record raw values and pass/fail):

1. **Coverage completeness**: percent of coverage-matrix rows in status `done`.
2. **Schema stability**: columns exactly match the stable ontology.
3. **Determinism**: repeated generation yields byte-identical artifacts.
4. **Link validity**: percent of non-empty `link` values that resolve to existing repo paths.
5. **Review divergence (optional)**: qualitative/quantitative divergence across reviewers/branches.

## Thresholds

- Coverage completeness: **>= 60% by Cycle 3**, **>= 80% by Cycle 5**
- Schema stability: **must pass every cycle** (no column drift)
- Determinism: **must pass every cycle**
- Link validity: **>= 95%** once links are introduced (otherwise N/A)
- Review divergence: **>= 0.95 consistency score** (if measured)

## What to do next (decision rules)

- If **schema stability fails**: stop; revert schema changes; regenerate; add a check to prevent reoccurrence.
- If **determinism fails**: stop; remove sources of nondeterminism (timestamps, unordered dicts); regenerate until identical.
- If **coverage completeness is below threshold**: prioritize creating missing artifacts; update coverage_matrix statuses.
- If **link validity is below threshold**: fix paths/links; avoid external/unstable URLs; re-check.
- If **metrics pass but quality issues remain**: add stricter checks or expand metrics; proceed to next cycle.
- If **all thresholds pass in Cycle 5**: tag/release; open a backlog for the next 5-cycle run.

"""
def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", newline="\n", delete=False, dir=str(path.parent)) as f:
        tmp = Path(f.name)
        f.write(text)
    tmp.replace(path)
def write_coverage_matrix_csv(outdir: Path) -> Path:
    outpath = outdir / "coverage_matrix.csv"
    outdir.mkdir(parents=True, exist_ok=True)
    # Deterministic row order and stable columns.
    rows = sorted(SEED_ROWS, key=lambda r: (r["domain"], r["subtopic"], r["artifact_type"]))
    with NamedTemporaryFile("w", encoding="utf-8", newline="\n", delete=False, dir=str(outdir)) as f:
        tmp = Path(f.name)
        writer = csv.DictWriter(f, fieldnames=COVERAGE_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in COVERAGE_COLUMNS})
    tmp.replace(outpath)
    return outpath
def write_eval_loop_md(outdir: Path) -> Path:
    outpath = outdir / "eval_loop.md"
    _atomic_write_text(outpath, EVAL_LOOP_MD.replace("\r\n", "\n"))
    return outpath
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generate deterministic outputs artifacts.")
    p.add_argument("--outdir", default="outputs", help="Output directory (default: outputs)")
    args = p.parse_args(argv)

    outdir = Path(args.outdir)
    write_coverage_matrix_csv(outdir)
    write_eval_loop_md(outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
