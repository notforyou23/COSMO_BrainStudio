from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
from typing import Any, Dict, Iterable, List, Optional, Tuple


STATUS_ORDER = ("PASS", "WARN", "FAIL", "SKIP", "ERROR")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _as_list(x: Any) -> List[Any]:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]


def _coerce_status(x: Any) -> str:
    if x is None:
        return "ERROR"
    s = str(x).strip().upper()
    if s in {"PASSED", "OK", "SUCCESS"}:
        return "PASS"
    if s in {"WARNING"}:
        return "WARN"
    if s in {"FAILED"}:
        return "FAIL"
    if s not in set(STATUS_ORDER):
        return "ERROR"
    return s


def _status_rank(status: str) -> int:
    s = _coerce_status(status)
    try:
        return STATUS_ORDER.index(s)
    except ValueError:
        return STATUS_ORDER.index("ERROR")


def _overall_status(counts: Dict[str, int]) -> str:
    if counts.get("ERROR", 0) > 0:
        return "ERROR"
    if counts.get("FAIL", 0) > 0:
        return "FAIL"
    if counts.get("WARN", 0) > 0:
        return "WARN"
    if counts.get("PASS", 0) > 0:
        return "PASS"
    return "SKIP"


def _safe_str(x: Any) -> str:
    if x is None:
        return ""
    if isinstance(x, str):
        return x
    return str(x)


def _coerce_check(item: Dict[str, Any]) -> Dict[str, Any]:
    cid = item.get("id") or item.get("check_id") or item.get("name") or "unknown_check"
    title = item.get("title") or item.get("name") or cid
    status = _coerce_status(item.get("status") or item.get("result") or item.get("outcome"))
    messages = _as_list(item.get("messages") or item.get("errors") or item.get("message"))
    remediation = _as_list(item.get("remediation") or item.get("fix") or item.get("pointers") or item.get("hints"))
    refs = _as_list(item.get("refs") or item.get("links") or item.get("documentation"))
    return {
        "id": _safe_str(cid),
        "title": _safe_str(title),
        "status": status,
        "messages": [m for m in (_safe_str(x) for x in messages) if m],
        "remediation": [r for r in (_safe_str(x) for x in remediation) if r],
        "refs": [r for r in (_safe_str(x) for x in refs) if r],
        "data": item.get("data") if isinstance(item.get("data"), (dict, list)) else item.get("data"),
    }


def build_report(check_results: Iterable[Dict[str, Any]], meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    checks = [_coerce_check(dict(x)) for x in (check_results or [])]
    checks.sort(key=lambda c: (_status_rank(c["status"]), c["id"]))
    counts: Dict[str, int] = {k: 0 for k in STATUS_ORDER}
    for c in checks:
        counts[c["status"]] = counts.get(c["status"], 0) + 1
    summary = {
        "generated_at": _utc_now_iso(),
        "overall_status": _overall_status(counts),
        "counts": counts,
        "total_checks": len(checks),
    }
    report: Dict[str, Any] = {
        "schema_version": "1.0",
        "summary": summary,
        "checks": checks,
        "meta": meta or {},
    }
    return report


def _md_escape(s: str) -> str:
    return s.replace("\", "\\").replace("|", "\|").replace("
", " ").strip()


def _md_status_badge(status: str) -> str:
    s = _coerce_status(status)
    return {"PASS": "PASS", "WARN": "WARN", "FAIL": "FAIL", "SKIP": "SKIP", "ERROR": "ERROR"}.get(s, "ERROR")


def render_markdown(report: Dict[str, Any]) -> str:
    summ = report.get("summary") or {}
    counts = summ.get("counts") or {}
    lines: List[str] = []
    lines.append("# QA Report")
    lines.append("")
    lines.append(f"- Generated at: `{_safe_str(summ.get('generated_at'))}`")
    lines.append(f"- Overall status: **{_md_status_badge(summ.get('overall_status'))}**")
    lines.append(f"- Total checks: **{summ.get('total_checks', len(report.get('checks') or []))}**")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| PASS | WARN | FAIL | SKIP | ERROR |")
    lines.append("|---:|---:|---:|---:|---:|")
    lines.append(
        f"| {counts.get('PASS', 0)} | {counts.get('WARN', 0)} | {counts.get('FAIL', 0)} | {counts.get('SKIP', 0)} | {counts.get('ERROR', 0)} |"
    )
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    checks = report.get("checks") or []
    if not checks:
        lines.append("_No checks were executed or no results were provided._")
        lines.append("")
        return "\n".join(lines).rstrip() + "\n"
    lines.append("| ID | Status | Title |")
    lines.append("|---|---|---|")
    for c in checks:
        lines.append(f"| `{_md_escape(c.get('id',''))}` | **{_md_status_badge(c.get('status'))}** | {_md_escape(c.get('title',''))} |")
    lines.append("")
    for c in checks:
        cid = _safe_str(c.get("id"))
        lines.append(f"### `{cid}` — {_md_status_badge(c.get('status'))}")
        lines.append("")
        title = _safe_str(c.get("title"))
        if title and title != cid:
            lines.append(f"**Title:** {title}")
            lines.append("")
        msgs = c.get("messages") or []
        if msgs:
            lines.append("**Messages:**")
            for m in msgs:
                lines.append(f"- {_safe_str(m)}")
            lines.append("")
        rem = c.get("remediation") or []
        if rem:
            lines.append("**Remediation:**")
            for r in rem:
                lines.append(f"- {_safe_str(r)}")
            lines.append("")
        refs = c.get("refs") or []
        if refs:
            lines.append("**References:**")
            for r in refs:
                lines.append(f"- {_safe_str(r)}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_json(path: Path, report: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def write_md(path: Path, report: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown(report), encoding="utf-8")


def write_reports(
    output_dir: Path,
    check_results: Optional[Iterable[Dict[str, Any]]] = None,
    report: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None,
    json_name: str = "QA_REPORT.json",
    md_name: str = "QA_REPORT.md",
) -> Dict[str, Any]:
    output_dir = Path(output_dir)
    if report is None:
        report = build_report(check_results or [], meta=meta)
    write_json(output_dir / json_name, report)
    write_md(output_dir / md_name, report)
    return report
