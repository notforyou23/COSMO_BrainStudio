"""Coverage matrix schema + deterministic CSV rendering.

This module defines a stable ontology (column schema) for a coverage matrix
and provides seed rows plus helpers to render/write the matrix to CSV.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Mapping, Sequence
import csv
import io
# Stable ontology columns (order must not change).
COLUMNS: Sequence[str] = ("domain", "subtopic", "artifact_type", "status", "link")


@dataclass(frozen=True)
class CoverageRow:
    """Typed row representation; renders to the stable ontology schema."""

    domain: str
    subtopic: str
    artifact_type: str
    status: str
    link: str = ""

    def as_dict(self) -> Mapping[str, str]:
        return {
            "domain": self.domain,
            "subtopic": self.subtopic,
            "artifact_type": self.artifact_type,
            "status": self.status,
            "link": self.link,
        }
def seed_rows() -> List[CoverageRow]:
    """Seed rows that establish expected artifacts and their locations."""

    return [
        CoverageRow(
            domain="outputs",
            subtopic="coverage_matrix",
            artifact_type="csv",
            status="planned",
            link="outputs/coverage_matrix.csv",
        ),
        CoverageRow(
            domain="outputs",
            subtopic="eval_loop",
            artifact_type="md",
            status="planned",
            link="outputs/eval_loop.md",
        ),
        CoverageRow(
            domain="scripts",
            subtopic="deterministic_generation",
            artifact_type="py",
            status="planned",
            link="scripts/generate_outputs.py",
        ),
        CoverageRow(
            domain="src",
            subtopic="coverage_matrix_renderer",
            artifact_type="module",
            status="planned",
            link="src/outputs/coverage_matrix.py",
        ),
        CoverageRow(
            domain="src",
            subtopic="eval_loop_renderer",
            artifact_type="module",
            status="planned",
            link="src/outputs/eval_loop.py",
        ),
        CoverageRow(
            domain="utils",
            subtopic="filesystem_atomic_writes",
            artifact_type="module",
            status="planned",
            link="src/utils/fs.py",
        ),
        CoverageRow(
            domain="utils",
            subtopic="csv_determinism",
            artifact_type="module",
            status="planned",
            link="src/utils/csv_utils.py",
        ),
    ]
def normalize_rows(rows: Iterable[Mapping[str, str] | CoverageRow]) -> List[Mapping[str, str]]:
    """Coerce inputs to dict rows with only the stable columns."""

    out: List[Mapping[str, str]] = []
    for r in rows:
        d = r.as_dict() if isinstance(r, CoverageRow) else dict(r)
        out.append({c: str(d.get(c, "")) for c in COLUMNS})
    return out


def render_csv(rows: Iterable[Mapping[str, str] | CoverageRow]) -> str:
    """Render rows to CSV with stable column order and \n newlines."""

    buf = io.StringIO(newline="")  # csv module controls newlines
    writer = csv.DictWriter(buf, fieldnames=list(COLUMNS), lineterminator="\n")
    writer.writeheader()
    for d in normalize_rows(rows):
        writer.writerow(d)
    return buf.getvalue()


def write_csv(path: str | Path, rows: Iterable[Mapping[str, str] | CoverageRow]) -> Path:
    """Write CSV to path (UTF-8) and return the resolved Path."""

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_csv(rows), encoding="utf-8", newline="\n")
    return p.resolve()


def default_matrix_csv() -> str:
    """Convenience helper returning the seed matrix rendered to CSV."""

    return render_csv(seed_rows())
