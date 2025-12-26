from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class MappingRecord:
    old_path: str
    new_path: str
    action: str  # moved/copied/skipped/linked/unknown
    category: str = ""
    reason: str = ""
    size_bytes: Optional[int] = None
    sha256: str = ""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _s(x: Any) -> str:
    return "" if x is None else str(x)


def _md_escape_cell(text: str) -> str:
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ").strip()


def _as_records(items: Iterable[Mapping[str, Any]]) -> List[MappingRecord]:
    out: List[MappingRecord] = []
    for it in items:
        out.append(
            MappingRecord(
                old_path=_s(it.get("old_path") or it.get("src") or it.get("from")),
                new_path=_s(it.get("new_path") or it.get("dst") or it.get("to")),
                action=_s(it.get("action") or "unknown"),
                category=_s(it.get("category") or ""),
                reason=_s(it.get("reason") or it.get("note") or ""),
                size_bytes=it.get("size_bytes") if isinstance(it.get("size_bytes"), int) else None,
                sha256=_s(it.get("sha256") or ""),
            )
        )
    return out


def _count_by(records: Sequence[MappingRecord], attr: str) -> List[Tuple[str, int]]:
    counts: Dict[str, int] = {}
    for r in records:
        k = getattr(r, attr) or ""
        counts[k] = counts.get(k, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))


def _md_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    hs = [_md_escape_cell(_s(h)) for h in headers]
    lines = ["| " + " | ".join(hs) + " |", "| " + " | ".join(["---"] * len(hs)) + " |"]
    for row in rows:
        cells = [_md_escape_cell(_s(c)) for c in row]
        if len(cells) < len(hs):
            cells += [""] * (len(hs) - len(cells))
        lines.append("| " + " | ".join(cells[: len(hs)]) + " |")
    return "\n".join(lines)


def _normalize_path(p: str) -> str:
    p = _s(p).strip()
    if not p:
        return ""
    return p.replace("\\", "/")


def write_canonicalization_report(
    report_path: Path,
    *,
    project_name: str = "",
    records: Optional[Iterable[Mapping[str, Any]]] = None,
    discovered: Optional[Iterable[Mapping[str, Any]]] = None,
    summary: Optional[Mapping[str, Any]] = None,
    notes: Optional[Sequence[str]] = None,
) -> str:
    """Write CANONICALIZATION_REPORT.md and return markdown text.

    Expected inputs:
      - records: iterable of dicts w/ old_path/new_path/action/category/reason/size_bytes/sha256.
      - discovered: optional iterable of dicts describing discovered artifacts (any keys).
      - summary: optional precomputed summary fields (e.g., totals).
    """
    report_path = Path(report_path)
    recs = _as_records(records or [])
    recs = sorted(
        recs,
        key=lambda r: (
            r.action,
            r.category,
            _normalize_path(r.old_path),
            _normalize_path(r.new_path),
        ),
    )

    summ: Dict[str, Any] = dict(summary or {})
    summ.setdefault("total_records", len(recs))
    summ.setdefault("generated_utc", _utc_now_iso())
    if project_name and "project" not in summ:
        summ["project"] = project_name

    by_action = _count_by(recs, "action")
    by_category = _count_by(recs, "category")

    lines: List[str] = []
    lines.append("# Canonicalization Report")
    lines.append("")
    if summ.get("project"):
        lines.append(f"**Project:** {_md_escape_cell(_s(summ.get('project')))}")
    lines.append(f"**Generated (UTC):** {_md_escape_cell(_s(summ.get('generated_utc')))}")
    lines.append(f"**Total artifacts in mapping:** {int(summ.get('total_records') or 0)}")
    lines.append("")

    if notes:
        lines.append("## Notes")
        lines.append("")
        for n in notes:
            n = _s(n).strip()
            if n:
                lines.append(f"- {n}")
        lines.append("")

    lines.append("## Summary")
    lines.append("")
    if by_action:
        lines.append("### By action")
        lines.append("")
        lines.append(_md_table(["action", "count"], [[a or "(blank)", c] for a, c in by_action]))
        lines.append("")
    if by_category:
        lines.append("### By category")
        lines.append("")
        lines.append(_md_table(["category", "count"], [[k or "(blank)", c] for k, c in by_category]))
        lines.append("")

    if discovered:
        disc = list(discovered)
        lines.append("## Discovered artifacts (raw)")
        lines.append("")
        lines.append(f"Count: {len(disc)}")
        lines.append("")
        show = []
        for d in disc:
            if not isinstance(d, Mapping):
                continue
            oldp = _s(d.get("path") or d.get("old_path") or d.get("src") or "")
            cat = _s(d.get("category") or "")
            kind = _s(d.get("kind") or d.get("type") or "")
            sizeb = d.get("size_bytes")
            show.append([oldp, cat, kind, sizeb if isinstance(sizeb, int) else ""])
        show = sorted(show, key=lambda r: (_normalize_path(_s(r[0])), _s(r[1]), _s(r[2])))
        lines.append(_md_table(["path", "category", "kind", "size_bytes"], show[:1000]))
        if len(show) > 1000:
            lines.append("")
            lines.append(f"_Truncated: showing first 1000 of {len(show)} discovered artifacts._")
        lines.append("")

    lines.append("## Old → New mapping")
    lines.append("")
    if not recs:
        lines.append("_No mapping records were provided._")
        lines.append("")
    else:
        rows = []
        for r in recs:
            rows.append(
                [
                    r.action,
                    r.category,
                    r.old_path,
                    r.new_path,
                    r.size_bytes if r.size_bytes is not None else "",
                    r.sha256,
                    r.reason,
                ]
            )
        lines.append(
            _md_table(
                ["action", "category", "old_path", "new_path", "size_bytes", "sha256", "reason"],
                rows,
            )
        )
        lines.append("")

    text = "\n".join(lines).rstrip() + "\n"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(text, encoding="utf-8")
    return text
__all__ = ["MappingRecord", "write_canonicalization_report"]
