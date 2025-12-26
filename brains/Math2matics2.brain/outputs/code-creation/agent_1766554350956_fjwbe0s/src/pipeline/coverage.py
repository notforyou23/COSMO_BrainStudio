"""Coverage matrix generator.

Maps mission requirements to produced artifacts, detecting gaps, and emits both:
- machine-readable JSON matrix
- human-readable Markdown matrix
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union
import json
@dataclass(frozen=True)
class Requirement:
    id: str
    title: str
    description: str = ""
    patterns: Tuple[str, ...] = ()
    tags: Tuple[str, ...] = ()

    def match(self, artifacts: Sequence[str]) -> List[str]:
        hits: List[str] = []
        for a in artifacts:
            for pat in self.patterns:
                if pat and fnmatch(a, pat):
                    hits.append(a)
                    break
        return sorted(set(hits))
DEFAULT_REQUIREMENTS: Tuple[Requirement, ...] = (
    Requirement(
        id="R1",
        title="Outputs-first runnable pipeline CLI",
        description="A runnable pipeline that immediately generates outputs and captures logs/results.",
        patterns=("src/run_pipeline.py", "outputs/**", "outputs/**/*.log", "outputs/**/*.json", "outputs/**/*.md"),
        tags=("pipeline", "outputs-first"),
    ),
    Requirement(
        id="R2",
        title="Captured logs/results",
        description="Pipeline execution produces captured logs/results artifacts.",
        patterns=("outputs/**/*.log", "outputs/**/results*.json", "outputs/**/results*.md", "outputs/**/run*.json"),
        tags=("outputs", "logging"),
    ),
    Requirement(
        id="R3",
        title="Roadmap artifact",
        description="Roadmap is generated as a stable, inspectable artifact.",
        patterns=("outputs/**/roadmap*.md", "outputs/**/roadmap*.json", "outputs/roadmap.md"),
        tags=("roadmap",),
    ),
    Requirement(
        id="R4",
        title="Bibliography system + seed .bib",
        description="BibTeX validation/normalization with a seed references.bib.",
        patterns=("src/pipeline/bibliography.py", "**/references.bib", "outputs/**/bibliography*.md", "outputs/**/bibliography*.json"),
        tags=("bibliography", "bibtex"),
    ),
    Requirement(
        id="R5",
        title="Coverage matrix generation",
        description="Coverage matrix maps requirements to artifacts and records gaps.",
        patterns=("src/pipeline/coverage.py", "outputs/**/coverage*.md", "outputs/**/coverage*.json"),
        tags=("coverage",),
    ),
    Requirement(
        id="R6",
        title="Checklist in outputs/index.md",
        description="Checklist aggregating milestones is written to outputs/index.md.",
        patterns=("outputs/index.md",),
        tags=("checklist", "outputs"),
    ),
    Requirement(
        id="R7",
        title="CI/CD consideration",
        description="Artifacts or docs addressing CI/CD (e.g., GitHub Actions config or notes).",
        patterns=(".github/workflows/*.yml", ".github/workflows/*.yaml", "outputs/**/ci*.md", "outputs/**/cicd*.md", "outputs/**/ci*.json"),
        tags=("cicd", "ci", "cd"),
    ),
)
def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def normalize_artifacts(artifacts: Iterable[Union[str, Path]]) -> List[str]:
    out: List[str] = []
    for a in artifacts:
        p = a.as_posix() if isinstance(a, Path) else str(a)
        p = p.replace("\\", "/").lstrip("./")
        out.append(p)
    return sorted(set(out))

def compute_coverage(
    artifacts: Iterable[Union[str, Path]],
    requirements: Sequence[Requirement] = DEFAULT_REQUIREMENTS,
    *,
    metadata: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    arts = normalize_artifacts(artifacts)
    req_rows: List[Dict[str, object]] = []
    covered = 0
    for r in requirements:
        hits = r.match(arts)
        is_gap = len(hits) == 0
        if not is_gap:
            covered += 1
        req_rows.append(
            {
                "id": r.id,
                "title": r.title,
                "description": r.description,
                "tags": list(r.tags),
                "patterns": list(r.patterns),
                "artifacts": hits,
                "gap": is_gap,
            }
        )
    total = len(requirements)
    gaps = total - covered
    matrix: Dict[str, object] = {
        "schema": "coverage-matrix.v1",
        "generated_at": _utc_now_iso(),
        "summary": {
            "requirements_total": total,
            "requirements_covered": covered,
            "requirements_gaps": gaps,
            "coverage_ratio": (covered / total) if total else 1.0,
        },
        "requirements": req_rows,
        "artifacts_index": arts,
    }
    if metadata:
        matrix["metadata"] = metadata
    return matrix
def render_markdown(matrix: Dict[str, object]) -> str:
    s = matrix.get("summary", {}) or {}
    total = s.get("requirements_total", 0)
    covered = s.get("requirements_covered", 0)
    gaps = s.get("requirements_gaps", 0)
    ratio = s.get("coverage_ratio", 0.0)
    gen = matrix.get("generated_at", "")
    lines: List[str] = []
    lines.append("# Coverage Matrix")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{gen}`")
    lines.append(f"- Requirements: **{covered} covered** / **{total} total** (gaps: **{gaps}**, ratio: **{ratio:.2f}**)")
    lines.append("")
    lines.append("| ID | Requirement | Status | Artifacts |")
    lines.append("|---:|---|---|---|")
    for r in matrix.get("requirements", []) or []:
        rid = str(r.get("id", ""))
        title = str(r.get("title", "")).replace("|", "\\|")
        gap = bool(r.get("gap", False))
        status = "GAP" if gap else "OK"
        arts = r.get("artifacts", []) or []
        arts_s = "<br>".join(str(a).replace("|", "\\|") for a in arts) if arts else ""
        lines.append(f"| {rid} | {title} | {status} | {arts_s} |")
    lines.append("")
    lines.append("## Gaps")
    gap_rows = [r for r in (matrix.get('requirements', []) or []) if r.get('gap')]
    if not gap_rows:
        lines.append("- None")
    else:
        for r in gap_rows:
            rid = r.get("id", "")
            title = r.get("title", "")
            pats = r.get("patterns", []) or []
            pat_s = ", ".join(f"`{p}`" for p in pats) if pats else "(no patterns)"
            lines.append(f"- **{rid}** {title} — expected: {pat_s}")
    lines.append("")
    return "\n".join(lines)
def _atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{datetime.now().strftime('%Y%m%d%H%M%S%f')}")
    tmp.write_text(text, encoding=encoding)
    tmp.replace(path)

def write_coverage_artifacts(
    output_dir: Union[str, Path],
    artifacts: Iterable[Union[str, Path]],
    requirements: Sequence[Requirement] = DEFAULT_REQUIREMENTS,
    *,
    prefix: str = "coverage",
    metadata: Optional[Dict[str, object]] = None,
) -> Dict[str, Path]:
    out = Path(output_dir)
    matrix = compute_coverage(artifacts, requirements, metadata=metadata)
    md = render_markdown(matrix)
    json_path = out / f"{prefix}.json"
    md_path = out / f"{prefix}.md"
    _atomic_write_text(json_path, json.dumps(matrix, indent=2, sort_keys=True) + "\n")
    _atomic_write_text(md_path, md + "\n")
    return {"json": json_path, "markdown": md_path}
