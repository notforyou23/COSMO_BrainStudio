from __future__ import annotations

from pathlib import Path
import csv
from datetime import date

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "outputs"

ARTIFACT_TYPES = [
    "lesson_note",
    "worked_examples",
    "problem_set",
    "quiz",
    "project",
    "reference_sheet",
]

DOMAINS = {
    "Number & Operations": [
        "Place value & number sense",
        "Fractions, decimals, percents",
        "Ratio, rate, proportional reasoning",
        "Integers & rational numbers",
    ],
    "Algebra": [
        "Expressions & equivalence",
        "Linear equations & inequalities",
        "Systems of equations",
        "Polynomials & factoring",
    ],
    "Functions": [
        "Function notation & representations",
        "Linear, quadratic, exponential models",
        "Transformations & inverses",
        "Composition & piecewise functions",
    ],
    "Geometry": [
        "Congruence & similarity",
        "Triangles & trigonometry basics",
        "Coordinate geometry",
        "Circles",
    ],
    "Measurement": [
        "Units & dimensional analysis",
        "Perimeter, area, volume",
        "Scale drawings & conversions",
        "Precision, error, estimation",
    ],
    "Statistics & Probability": [
        "Data displays & summaries",
        "Center, spread, and shape",
        "Probability models",
        "Inference basics (sampling, CI intuition)",
    ],
    "Calculus": [
        "Limits & continuity",
        "Derivatives & applications",
        "Integrals & accumulation",
        "Series basics",
    ],
    "Discrete Mathematics": [
        "Logic & proof techniques",
        "Combinatorics",
        "Graph theory fundamentals",
        "Recurrence relations",
    ],
    "Linear Algebra": [
        "Vectors & geometry",
        "Matrices & linear systems",
        "Determinants & eigenvalues",
        "Vector spaces & linear maps",
    ],
}
def write_coverage_matrix_csv(path: Path) -> None:
    """Create a starter coverage matrix with at least one example row per domain."""
    headers = [
        "domain",
        "subtopic",
        "detail",
        "priority",
        "cross_links",
        *[f"count_{t}" for t in ARTIFACT_TYPES],
        "notes",
    ]

    rows = []
    for domain, subtopics in DOMAINS.items():
        sub = subtopics[0]
        rows.append(
            {
                "domain": domain,
                "subtopic": sub,
                "detail": "Example row: expand with finer subskills, standards, and artifact IDs.",
                "priority": "P1",
                "cross_links": "",
                **{f"count_{t}": 0 for t in ARTIFACT_TYPES},
                "notes": "Populate counts as artifacts are created; add more rows per subtopic.",
            }
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        w.writerows(rows)
def write_eval_loop_md(path: Path) -> None:
    cadence = [
        ("Cycle 1", "Baseline inventory & taxonomy alignment"),
        ("Cycle 2", "Fill highest-priority gaps; create cross-links"),
        ("Cycle 3", "Depth pass: more examples/assessments; reduce redundancy"),
        ("Cycle 4", "Consistency & quality review; align terminology and notation"),
        ("Cycle 5", "Stabilize: retire/merge, finalize coverage report"),
    ]

    metric_lines = [
        "- Artifact count by type (sum of count_* columns; plus per-domain totals).",
        "- Cross-links: number of non-empty cross_links cells; and average links per row.",
        "- Coverage gaps: rows where all count_* are 0; plus missing subtopics vs. domain list.",
        "- Balance: domains with <N artifacts total (default N=3) flagged for attention.",
        "- Churn: artifacts retired/merged this cycle (tracked in notes).",
    ]

    decision_rules = [
        "**Produce next** when: (a) a domain has gaps (all counts 0) in P1 rows; "
        "(b) a domain total < N=3; or (c) cross-links average < 1.0.",
        "**Link next** when: the same skill appears in multiple domains (e.g., functions ↔ algebra) "
        "and cross_links is empty; add at least 1 bidirectional link per affected row.",
        "**Deepen next** when: lesson_note exists but quiz/problem_set is 0; prioritize assessment artifacts.",
        "**Retire/Merge** when: two artifacts cover the same subtopic with >80% overlap; keep the clearer one, "
        "set the other to retired in notes and decrement its count.",
        "**Deprioritize** when: a row is P3 and the domain already meets N; do not create new artifacts there this cycle.",
    ]

    lines = []
    lines.append("# 5-Cycle Evaluation Loop\n")
    lines.append(f"_Generated: {date.today().isoformat()}_\n")
    lines.append("## Cadence\n")
    lines.append("| Cycle | Focus | Deliverable |")
    lines.append("|---|---|---|")
    for c, focus in cadence:
        lines.append(f"| {c} | {focus} | Update coverage_matrix.csv + brief cycle notes in this file |")

    lines.append("\n## Metrics to record each cycle\n")
    lines.extend(metric_lines)

    lines.append("\n## Procedure (each cycle)\n")
    lines.append("1. Recompute metrics from `outputs/coverage_matrix.csv`.")
    lines.append("2. List the top 5 coverage gaps (P1 first) and top 5 weakly-linked rows.")
    lines.append("3. Apply decision rules to choose what to produce, link, deepen, or retire.")
    lines.append("4. Update counts and cross_links; add a short 'Cycle Notes' section with changes.")
    lines.append("5. Lock the cycle by committing the updated outputs.")

    lines.append("\n## Decision rules\n")
    lines.extend([f"- {r}" for r in decision_rules])

    lines.append("\n## Cycle Notes Template\n")
    lines.append("### Cycle X Notes")
    lines.append("- Metrics snapshot: artifacts_by_type=…, cross_links=…, coverage_gaps=…")
    lines.append("- Produced: …")
    lines.append("- Linked: …")
    lines.append("- Retired/Merged: …")
    lines.append("- Next cycle focus: …\n")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_coverage_matrix_csv(OUTPUT_DIR / "coverage_matrix.csv")
    write_eval_loop_md(OUTPUT_DIR / "eval_loop.md")


if __name__ == "__main__":
    main()
