#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Dict, Tuple

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = ROOT / "outputs"

ARTIFACT_TYPES: Tuple[str, ...] = (
    "overview",          # high-level explainer / notes
    "worked_examples",   # solved problems
    "exercises",         # practice prompts
    "solutions",         # answer keys
    "implementation",    # code / algorithms where relevant
    "tests",             # verification / unit tests
    "references",        # citations / links
)

TAXONOMY: Dict[str, List[str]] = {
    "Algebra": ["Linear equations", "Polynomials", "Abstract algebra"],
    "Calculus": ["Limits", "Derivatives", "Integrals", "Series"],
    "Discrete Mathematics": ["Logic", "Combinatorics", "Graph theory", "Number theory"],
    "Geometry": ["Euclidean geometry", "Analytic geometry", "Linear algebra geometry"],
    "Probability & Statistics": ["Probability", "Random variables", "Inference"],
}

CSV_HEADERS: Tuple[str, ...] = (
    "cell_id",
    "domain",
    "subtopic",
    "artifact_type",
    "status",
    "primary_link",
    "cross_links",
)

STATUS_DEFAULT = "uncovered"


@dataclass(frozen=True)
class Cell:
    cell_id: str
    domain: str
    subtopic: str
    artifact_type: str
    status: str = STATUS_DEFAULT
    primary_link: str = ""
    cross_links: str = ""


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text.replace("\r\n", "\n").replace("\r", "\n"), encoding="utf-8", newline="\n")
    tmp.replace(path)


def _atomic_write_csv(path: Path, rows: Iterable[Dict[str, str]], headers: Tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(headers), lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in headers})
    tmp.replace(path)


def iter_cells() -> List[Cell]:
    out: List[Cell] = []
    for domain in sorted(TAXONOMY):
        for subtopic in TAXONOMY[domain]:
            for atype in ARTIFACT_TYPES:
                cell_id = f"math::{domain}::{subtopic}::{atype}".replace(" ", "_").lower()
                out.append(Cell(cell_id=cell_id, domain=domain, subtopic=subtopic, artifact_type=atype))
    return out


def render_markdown_table(cells: List[Cell]) -> str:
    lines = [
        "# Mathematics coverage matrix (cells)",
        "",
        "| domain | subtopic | artifact_type | status | primary_link | cross_links |",
        "|---|---|---|---|---|---|",
    ]
    for c in cells:
        lines.append(f"| {c.domain} | {c.subtopic} | {c.artifact_type} | {c.status} | {c.primary_link} | {c.cross_links} |")
    lines.append("")
    return "\n".join(lines)


def render_eval_loop_md(total_cells: int) -> str:
    return "\n".join([
        "# Mathematics evaluation loop (5-cycle cadence)",
        "",
        "This document defines a deterministic review cadence for the Mathematics domain artifacts generated from the coverage matrix.",
        "",
        "## Inputs",
        f"- Coverage matrix: `outputs/coverage_matrix.csv` ({total_cells} cells = domains × subtopics × artifact types).",
        "- Optional table: `outputs/coverage_matrix.md` (human scanning only).",
        "",
        "## Metrics to track (per cycle)",
        "- **artifact_count**: number of produced artifacts that map to cells (status != `uncovered`).",
        "- **cross_links_count**: total non-empty cross-links; and average cross-links per covered cell.",
        "- **uncovered_cells**: count of cells with status `uncovered` (goal: monotone decrease).",
        "- **coverage_by_domain**: covered cells / total cells per domain (detect imbalance).",
        "- **staleness**: days since last update per domain/subtopic (optional, if timestamps exist).",
        "",
        "## 5-cycle review cadence",
        "1. **Cycle 1 — Inventory & gaps**: validate taxonomy, count uncovered cells, and pick the smallest set of artifacts that unlock the most downstream work.",
        "2. **Cycle 2 — Core explanations**: create/upgrade `overview` artifacts for the highest-priority subtopics; add references and minimal cross-links.",
        "3. **Cycle 3 — Worked examples**: produce `worked_examples` aligned to each overview; ensure each example links back to its overview and prerequisite cells.",
        "4. **Cycle 4 — Exercises + solutions**: add `exercises` and `solutions` for cells that already have an overview (avoid orphan exercises).",
        "5. **Cycle 5 — Implementation + tests + refactor**: add computational artifacts where meaningful; create tests; standardize formatting and cross-links.",
        "",
        "## Decision rules (what to create next)",
        "Apply in order; stop at the first rule that selects work:",
        "1. **Unblock rule**: If any domain has `overview` coverage < 50%, create overviews there first.",
        "2. **Dependency rule**: For a subtopic, do not create `exercises` unless `overview` exists; do not create `tests` unless `implementation` exists.",
        "3. **Balance rule**: If one domain's coverage ratio is > 2× another's, prioritize the least-covered domain until ratios normalize.",
        "4. **Cross-link rule**: If covered cells have average cross-links < 2, prioritize adding prerequisite/related links before creating new artifacts.",
        "5. **Lowest-effort rule**: Choose the next cell that can be completed with the smallest artifact that increases coverage (typically: `overview` → `worked_examples`).",
        "",
        "## Status field semantics (for the matrix)",
        "- `uncovered`: no artifact exists for this cell.",
        "- `draft`: artifact exists but needs review/corrections.",
        "- `reviewed`: content checked for correctness and clarity.",
        "- `complete`: stable; only minor edits expected.",
        "",
        "## Updating the matrix",
        "- When an artifact is created, set the corresponding cell status to at least `draft` and set `primary_link` to a stable path/URL.",
        "- Add `cross_links` as a semicolon-separated list of other cell_ids or stable paths.",
        "",
    ]) + "\n"


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generate Mathematics coverage matrix and evaluation loop policy.")
    p.add_argument("--outputs-dir", default=str(OUTPUTS_DIR), help="Output directory (default: repo_root/outputs).")
    p.add_argument("--write-markdown", action="store_true", help="Also write outputs/coverage_matrix.md.")
    args = p.parse_args(argv)

    outdir = Path(args.outputs_dir)
    cells = iter_cells()

    csv_path = outdir / "coverage_matrix.csv"
    _atomic_write_csv(csv_path, (c.__dict__ for c in cells), CSV_HEADERS)

    if args.write_markdown:
        md_path = outdir / "coverage_matrix.md"
        _atomic_write_text(md_path, render_markdown_table(cells))

    eval_path = outdir / "eval_loop.md"
    _atomic_write_text(eval_path, render_eval_loop_md(total_cells=len(cells)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
