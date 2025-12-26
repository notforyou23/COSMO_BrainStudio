"""Rendering utilities for deterministic, inspectable output artifacts.

This module serializes a coverage matrix (list of row dicts) to:
- machine-readable CSV (for downstream tooling)
- optional Markdown table (for human inspection)
and emits a Markdown evaluation loop policy document.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
from typing import Iterable, Mapping, Sequence, Any, Optional, List, Tuple
@dataclass(frozen=True)
class CoverageSchema:
    """Stable column order for the coverage matrix."""

    columns: Tuple[str, ...] = (
        "domain",
        "subtopic",
        "artifact_type",
        "status",
        "cross_links",
    )


def _escape_md(text: Any) -> str:
    s = "" if text is None else str(text)
    return s.replace("|", "\|").replace("
", "<br>")
def render_coverage_csv_text(
    rows: Iterable[Mapping[str, Any]],
    schema: CoverageSchema = CoverageSchema(),
) -> str:
    """Return coverage matrix as CSV text with stable headers and newlines."""
    out_lines: List[str] = []
    # Use csv.writer to ensure proper quoting, but write into a string buffer via list.
    class _Buf:
        def write(self, s: str) -> None:  # pragma: no cover
            out_lines.append(s)

    buf = _Buf()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(schema.columns)
    for row in rows:
        w.writerow([row.get(col, "") for col in schema.columns])
    return "".join(out_lines)


def write_coverage_csv(
    rows: Iterable[Mapping[str, Any]],
    output_path: Path,
    schema: CoverageSchema = CoverageSchema(),
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_coverage_csv_text(rows, schema), encoding="utf-8")
def render_coverage_markdown_table(
    rows: Sequence[Mapping[str, Any]],
    schema: CoverageSchema = CoverageSchema(),
    title: Optional[str] = None,
) -> str:
    """Return a GitHub-flavored Markdown table for the coverage matrix."""
    cols = list(schema.columns)
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join(["---"] * len(cols)) + " |"
    body = []
    for row in rows:
        body.append(
            "| " + " | ".join(_escape_md(row.get(c, "")) for c in cols) + " |"
        )
    parts = []
    if title:
        parts.append(f"## {title}\n")
    parts.extend([header, sep, *body])
    return "\n".join(parts).rstrip() + "\n"


def write_coverage_markdown(
    rows: Sequence[Mapping[str, Any]],
    output_path: Path,
    schema: CoverageSchema = CoverageSchema(),
    title: Optional[str] = None,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_coverage_markdown_table(rows, schema=schema, title=title),
        encoding="utf-8",
    )
def render_eval_loop_markdown(domain_name: str = "Mathematics") -> str:
    """Return the 5-cycle evaluation-loop policy document as Markdown."""
    return f"""# Evaluation Loop Policy ({domain_name})

This document defines a deterministic, repeatable 5-cycle review cadence for improving artifact coverage.

## Artifacts tracked
- Coverage matrix CSV: `coverage_matrix.csv`
- Optional coverage matrix Markdown table
- Evaluation loop policy: `eval_loop.md`

## Core metrics (computed from the coverage matrix)
1. **artifact_count**: number of rows (domain × subtopic × artifact_type).
2. **cross_link_count**: number of rows where `cross_links` is non-empty and not `TBD`.
3. **uncovered_cell_count**: number of rows where `status` is one of: `missing`, `planned`, `stub`.
4. **ready_count**: number of rows where `status` is `ready`.
5. **coverage_ratio**: `ready_count / artifact_count` (if `artifact_count > 0`).

## Status vocabulary (recommended)
- `missing`: not created at all.
- `planned`: acknowledged but not yet created.
- `stub`: exists but incomplete (needs expansion, examples, proofs, exercises, etc.).
- `ready`: complete enough for downstream use; cross-links added where relevant.

## 5-cycle cadence
### Cycle 1 — Baseline inventory
- Generate the matrix from the taxonomy.
- Verify headers, stable ordering, and row count.
- Mark obvious gaps as `missing` (not `planned`) to avoid hiding work.

### Cycle 2 — Fill highest-impact gaps
- Prioritize uncovered cells that unblock multiple subtopics (foundational definitions/theorems).
- Add at least one cross-link per foundational artifact where applicable.

### Cycle 3 — Add cross-links and coherence
- Increase `cross_link_count` by connecting prerequisites, related results, and examples.
- Normalize naming so links are searchable and consistent.

### Cycle 4 — Depth pass
- Upgrade `stub → ready` for artifacts with the most inbound cross-links (most reused).
- Add proofs, worked examples, and common pitfalls.

### Cycle 5 — Audit and stabilize
- Recompute metrics and ensure `uncovered_cell_count` is trending down.
- Freeze schema/headers; any taxonomy changes should be explicit and versioned.

## Decision rules: what to create next
Given the current `coverage_matrix.csv`, choose the next creation/upgrade task using:

1. **Uncovered-first rule**
   - If `uncovered_cell_count > 0`, select the uncovered row with:
     - highest expected reuse (foundational subtopic), then
     - lowest effort (small, well-scoped artifact), then
     - largest cross-link potential (many related subtopics).

2. **Cross-link rule**
   - If `coverage_ratio ≥ 0.80` and `cross_link_count / artifact_count < 0.50`,
     prioritize adding cross-links to `ready` artifacts before creating new ones.

3. **Stub-upgrade rule**
   - If there are `stub` rows, prioritize the `stub` with the most references in `cross_links`
     (or the one belonging to the most central domain).

4. **Schema-change rule**
   - If new domains/subtopics/artifact types are introduced, regenerate the matrix and
     require that `artifact_count` increases by the expected delta; otherwise reject the change.

## Exit criteria
The loop is considered "healthy" when:
- `coverage_ratio` increases each cycle (or remains stable while `cross_link_count` increases),
- `uncovered_cell_count` decreases each cycle (or is zero),
- outputs remain deterministic (stable diffs under identical inputs).
"""
def write_eval_loop_markdown(output_path: Path, domain_name: str = "Mathematics") -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_eval_loop_markdown(domain_name), encoding="utf-8")
