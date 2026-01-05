from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import json


Issue = Dict[str, Any]
Report = Dict[str, Any]


def make_issue(
    kind: str,
    message: str,
    *,
    file: Optional[str] = None,
    record: Optional[str] = None,
    field: Optional[str] = None,
    expected: Optional[str] = None,
    found: Optional[str] = None,
    study_id: Optional[str] = None,
    effect_id: Optional[str] = None,
    severity: str = "error",
    extra: Optional[Dict[str, Any]] = None,
) -> Issue:
    """Create a normalized issue object suitable for JSON output and text rendering."""
    loc: Dict[str, Any] = {}
    if file is not None:
        loc["file"] = file
    if record is not None:
        loc["record"] = record
    if field is not None:
        loc["field"] = field

    iss: Issue = {
        "kind": kind,
        "severity": severity,
        "message": message,
    }
    if loc:
        iss["location"] = loc
    if expected is not None:
        iss["expected"] = expected
    if found is not None:
        iss["found"] = found
    if study_id is not None:
        iss["StudyID"] = study_id
    if effect_id is not None:
        iss["EffectID"] = effect_id
    if extra:
        iss.update(extra)
    return iss


def _counts(issues: Sequence[Issue]) -> Dict[str, int]:
    by_sev: Dict[str, int] = {}
    by_kind: Dict[str, int] = {}
    for it in issues:
        by_sev[it.get("severity", "error")] = by_sev.get(it.get("severity", "error"), 0) + 1
        k = it.get("kind", "unknown")
        by_kind[k] = by_kind.get(k, 0) + 1
    return {"total": len(issues), "by_severity": by_sev, "by_kind": by_kind}


def build_report(
    *,
    issues: Sequence[Issue],
    meta: Optional[Dict[str, Any]] = None,
    tool: str = "ids.checker",
    version: str = "0.1",
) -> Report:
    """Build the canonical report envelope."""
    meta_out = dict(meta or {})
    meta_out.setdefault("tool", tool)
    meta_out.setdefault("version", version)
    meta_out.setdefault("generated_at", datetime.now(timezone.utc).isoformat())

    counts = _counts(issues)
    ok = counts["by_severity"].get("error", 0) == 0
    return {"ok": ok, "meta": meta_out, "counts": counts, "issues": list(issues)}


def merge_reports(reports: Iterable[Report], *, meta: Optional[Dict[str, Any]] = None) -> Report:
    """Merge multiple reports into a single envelope."""
    issues: List[Issue] = []
    merged_meta: Dict[str, Any] = {}
    for r in reports:
        merged_meta.update(r.get("meta", {}) or {})
        issues.extend(r.get("issues", []) or [])
    if meta:
        merged_meta.update(meta)
    return build_report(issues=issues, meta=merged_meta)


def _fmt_loc(issue: Issue) -> str:
    loc = issue.get("location") or {}
    parts: List[str] = []
    if "file" in loc:
        parts.append(str(loc["file"]))
    if "record" in loc:
        parts.append(f"record={loc['record']}")
    if "field" in loc:
        parts.append(f"field={loc['field']}")
    return (" (" + ", ".join(parts) + ")") if parts else ""


def render_text(report: Report, *, max_issues: Optional[int] = None) -> str:
    """Render a human-readable summary."""
    counts = report.get("counts") or {}
    by_sev = (counts.get("by_severity") or {})
    by_kind = (counts.get("by_kind") or {})
    lines: List[str] = []
    lines.append(f"ID Integrity: {'PASS' if report.get('ok') else 'FAIL'}")
    lines.append(f"Issues: {counts.get('total', 0)} (errors={by_sev.get('error', 0)}, warnings={by_sev.get('warning', 0)})")
    if by_kind:
        kinds = ", ".join(f"{k}={by_kind[k]}" for k in sorted(by_kind))
        lines.append(f"Kinds: {kinds}")
    issues = report.get("issues") or []
    if not issues:
        return "\n".join(lines).rstrip() + "\n"

    limit = len(issues) if max_issues is None else max(0, min(len(issues), int(max_issues)))
    lines.append("\nDetails:")
    for i, iss in enumerate(issues[:limit], start=1):
        sev = iss.get("severity", "error").upper()
        kind = iss.get("kind", "unknown")
        msg = iss.get("message", "")
        loc = _fmt_loc(iss)
        ctx_parts: List[str] = []
        if iss.get("StudyID"):
            ctx_parts.append(f"StudyID={iss['StudyID']}")
        if iss.get("EffectID"):
            ctx_parts.append(f"EffectID={iss['EffectID']}")
        if iss.get("expected") is not None or iss.get("found") is not None:
            ctx_parts.append(f"expected={iss.get('expected')!r} found={iss.get('found')!r}")
        ctx = (" [" + ", ".join(ctx_parts) + "]") if ctx_parts else ""
        lines.append(f"  {i}. {sev} {kind}{loc}: {msg}{ctx}")
    if limit < len(issues):
        lines.append(f"  ... ({len(issues) - limit} more)")
    return "\n".join(lines).rstrip() + "\n"


def render_json(report: Report, *, indent: int = 2, sort_keys: bool = True) -> str:
    """Render a machine-readable JSON document."""
    return json.dumps(report, indent=indent, sort_keys=sort_keys, ensure_ascii=False) + "\n"
