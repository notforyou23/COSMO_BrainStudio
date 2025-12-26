#!/usr/bin/env python3
"""Generate project planning artifacts.

Outputs:
- outputs/coverage_matrix.csv : long-form, script-friendly coverage matrix
- outputs/coverage_matrix.md  : human-friendly table + update instructions
- outputs/eval_loop.md        : 5-cycle review cadence, metrics, decision rules

Usage:
  python scripts/generate_outputs.py
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
from datetime import date
@dataclass(frozen=True)
class Cell:
    status: str  # MISSING | PLANNED | IN_PROGRESS | COMPLETE | NEEDS_REVIEW
    count: int = 0
    links: str = ""  # semicolon-separated repo pointers or URLs

def seed_cells() -> dict[tuple[str, str], Cell]:
    # Key: (subtopic, artifact_type). Keep small seeds as inline examples.
    return {
        ("Calculus", "concept_notes"): Cell("PLANNED", 0, "notes/calculus/limits.md"),
        ("Linear Algebra", "worked_examples"): Cell("PLANNED", 0, "examples/linear_algebra/basis_change.md"),
        ("Probability", "practice_problems"): Cell("PLANNED", 0, "problems/probability/basic_sets.md"),
        ("Discrete Math", "proofs"): Cell("PLANNED", 0, "proofs/induction/template.md"),
    }
def build_rows() -> list[dict[str, str]]:
    domain = "Mathematics"
    subtopics = [
        "Arithmetic & Prealgebra",
        "Algebra",
        "Functions",
        "Geometry",
        "Trigonometry",
        "Calculus",
        "Linear Algebra",
        "Differential Equations",
        "Probability",
        "Statistics",
        "Discrete Math",
        "Number Theory",
        "Logic & Set Theory",
        "Optimization",
        "Numerical Methods",
    ]
    artifact_types = [
        "concept_notes",
        "worked_examples",
        "practice_problems",
        "quizzes",
        "proofs",
        "visuals",
        "code_notebooks",
        "reference_sheets",
    ]
    seeds = seed_cells()
    rows: list[dict[str, str]] = []
    for st in subtopics:
        for at in artifact_types:
            cell = seeds.get((st, at), Cell("MISSING", 0, ""))
            rows.append(
                {
                    "domain": domain,
                    "subtopic": st,
                    "artifact_type": at,
                    "status": cell.status,
                    "count": str(cell.count),
                    "links": cell.links,
                    "last_updated": date.today().isoformat(),
                }
            )
    return rows
def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["domain", "subtopic", "artifact_type", "status", "count", "links", "last_updated"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

def md_escape(s: str) -> str:
    return s.replace("|", "\\|")
def write_matrix_md(path: Path, rows: list[dict[str, str]]) -> None:
    # Compact pivot: one row per subtopic; each cell is "STATUS(count) -> links".
    artifact_types = []
    for r in rows:
        if r["artifact_type"] not in artifact_types:
            artifact_types.append(r["artifact_type"])
    subtopics = []
    for r in rows:
        if r["subtopic"] not in subtopics:
            subtopics.append(r["subtopic"])

    by = {(r["subtopic"], r["artifact_type"]): r for r in rows}

    lines = []
    lines.append("# Coverage matrix — Mathematics\n")
    lines.append("This is a *planning* matrix. Update the CSV first; regenerate this MD by rerunning the script.\n")
    lines.append("## Status vocabulary\n")
    lines.append("- MISSING: nothing exists yet\n- PLANNED: pointer exists, work not started\n- IN_PROGRESS\n- COMPLETE\n- NEEDS_REVIEW\n")
    lines.append("## Table (cells = STATUS(count) → links)\n")
    header = ["Subtopic"] + artifact_types
    lines.append("| " + " | ".join(header) + " |\n")
    lines.append("|" + "|".join(["---"] * len(header)) + "|\n")
    for st in subtopics:
        row = [st]
        for at in artifact_types:
            r = by[(st, at)]
            cell = f"{r['status']}({r['count']})"
            if r["links"]:
                cell += f" → {r['links']}"
            row.append(md_escape(cell))
        lines.append("| " + " | ".join(row) + " |\n")

    lines.append("\n## How to update (minimal example)\n")
    lines.append("Edit `outputs/coverage_matrix.csv` (or a derived source of truth) and change fields. Example row:\n\n")
    lines.append("```csv\n")
    lines.append("domain,subtopic,artifact_type,status,count,links,last_updated\n")
    lines.append("Mathematics,Calculus,concept_notes,IN_PROGRESS,1,notes/calculus/limits.md,2025-01-01\n")
    lines.append("```\n")
    lines.append("Conventions: `links` is semicolon-separated (e.g., `a.md;b.md`). `count` is the number of artifacts of that type for that subtopic.\n")
    path.write_text("".join(lines), encoding="utf-8")
def write_eval_loop_md(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    md = f"""# Evaluation loop (5-cycle cadence)

Purpose: drive measurable, repeatable expansion of Mathematics coverage while keeping artifacts cross-linked and reviewable.

## Cadence (repeat every planning iteration)
1. **Cycle 1 — Inventory & normalize**
   - Regenerate `coverage_matrix.csv`/`.md`.
   - Normalize subtopic names and artifact types (no duplicates; stable strings).
2. **Cycle 2 — Fill highest-impact gaps**
   - Produce artifacts for the largest *coverage gaps* (see metrics).
3. **Cycle 3 — Cross-linking & coherence**
   - Add prerequisite and "see also" links between artifacts/subtopics.
4. **Cycle 4 — Quality pass**
   - Run consistency review across branches/variants; fix divergences and mark NEEDS_REVIEW → COMPLETE.
5. **Cycle 5 — Regression & next-plan**
   - Recompute metrics; decide next cycle’s production targets using decision rules.

## Metrics (computed from `outputs/coverage_matrix.csv`)
- **Artifact count**: sum of `count` over rows.
- **Coverage ratio**: COMPLETE rows / total rows (optionally include IN_PROGRESS as partial).
- **Coverage gaps**:
  - A row with status MISSING or PLANNED and `count == 0` is a gap.
  - A subtopic gap score = number of gap rows for that subtopic.
- **Cross-link density**:
  - link_rows = number of rows where `links` is non-empty.
  - density = link_rows / total rows.

Minimal manual tally example:
- If a subtopic has 8 artifact types and 6 are MISSING, its gap score is 6.

## Decision rules (what to produce next)
Apply in order; stop when the planned work queue is full for the next cycle.

1. **If coverage ratio < 0.20**:
   - Produce `concept_notes` + 2 `worked_examples` for the top-3 subtopics by gap score.
2. **Else if any subtopic has gap score ≥ 5**:
   - Produce one artifact in each missing type for that subtopic, prioritizing:
     `concept_notes` → `worked_examples` → `practice_problems` → `quizzes`.
3. **Else if cross-link density < 0.35**:
   - Add/curate links: at least 2 links per subtopic (prereq + follow-on), stored in `links`.
4. **Else**:
   - Quality: convert IN_PROGRESS/NEEDS_REVIEW to COMPLETE by addressing review notes,
     and add `reference_sheets` for the 5 most-used subtopics.

## Update protocol (machine-friendly)
- Source of truth is `outputs/coverage_matrix.csv`.
- Update a cell by editing its row:
  - increment `count`
  - set `status`
  - append `links` using semicolons
  - refresh `last_updated` (ISO date)
- Then rerun: `python scripts/generate_outputs.py` to rebuild Markdown views.

## Notes
Prior consistency reviews reported high alignment across branches (divergence ~0.96–0.97). Use Cycle 4 to keep that divergence low as new artifacts are added.
"""
    path.write_text(md, encoding="utf-8")
def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "outputs"
    rows = build_rows()
    write_csv(out_dir / "coverage_matrix.csv", rows)
    write_matrix_md(out_dir / "coverage_matrix.md", rows)
    write_eval_loop_md(out_dir / "eval_loop.md")

if __name__ == "__main__":
    main()
