from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import re
from typing import Any, Callable, Dict, Iterable, List, Optional

Status = str  # "pass" | "fail" | "warn"

@dataclass(frozen=True)
class Check:
    id: str
    name: str
    remediation: str
    severity: str  # "error" | "warning"
    fn: Callable[[str, Dict[str, Any]], Dict[str, Any]]

_CHECKS: List[Check] = []

def register_check(check_id: str, name: str, remediation: str, severity: str = "error"):
    def deco(fn: Callable[[str, Dict[str, Any]], Dict[str, Any]]):
        _CHECKS.append(Check(check_id, name, remediation, severity, fn))
        return fn
    return deco

def _result(check: Check, ok: bool, messages: Optional[Iterable[str]] = None, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    status: Status = "pass" if ok else ("warn" if check.severity == "warning" else "fail")
    return {
        "id": check.id,
        "name": check.name,
        "status": status,
        "messages": [m for m in (messages or []) if m],
        "remediation": check.remediation,
        "details": details or {},
    }

def _artifact_paths(artifacts: Dict[str, Any]) -> List[Path]:
    out: List[Path] = []
    for v in (artifacts or {}).values():
        if isinstance(v, Path):
            out.append(v)
        elif isinstance(v, str):
            p = Path(v)
            if p.suffix:
                out.append(p)
        elif isinstance(v, dict) and isinstance(v.get("path"), (str, Path)):
            out.append(Path(v["path"]))
    return out

@register_check(
    "report_nonempty",
    "Report is present and non-trivial",
    "Ensure DRAFT_REPORT_v0.md exists, is readable, and contains substantive content (not just a stub).",
)
def check_report_nonempty(report_text: str, artifacts: Dict[str, Any]) -> Dict[str, Any]:
    n = len((report_text or "").strip())
    ok = n >= 400
    msgs = [] if ok else [f"Report content too short: {n} chars (expected >= 400)."]
    return _result(_CHECKS_BY_ID['report_nonempty'], ok, msgs, {"char_count": n})

@register_check(
    "required_sections",
    "Report contains required sections",
    "Add headings for: Executive Summary, Methods, Findings/Results, Risks/Limitations, and Recommendations/Next Steps.",
)
def check_required_sections(report_text: str, artifacts: Dict[str, Any]) -> Dict[str, Any]:
    text = report_text or ""
    required = ["Executive Summary", "Methods", "Findings", "Risks", "Recommendations"]
    missing = []
    for r in required:
        pat = re.compile(rf"^#{1,6}\s+.*{re.escape(r)}.*$", re.IGNORECASE | re.MULTILINE)
        if not pat.search(text):
            missing.append(r)
    ok = not missing
    msgs = [] if ok else [f"Missing section heading(s): {', '.join(missing)}."]
    return _result(_CHECKS_BY_ID['required_sections'], ok, msgs, {"missing": missing})

@register_check(
    "no_placeholders",
    "Report has no placeholder markers",
    "Remove placeholder tokens (TODO/TBD/XXX/lorem ipsum) and replace with final content or explicitly mark as a limitation.",
    severity="warning",
)
def check_no_placeholders(report_text: str, artifacts: Dict[str, Any]) -> Dict[str, Any]:
    text = report_text or ""
    tokens = ["TODO", "TBD", "XXX", "lorem ipsum", "PLACEHOLDER"]
    hits = [t for t in tokens if re.search(rf"\b{re.escape(t)}\b", text, re.IGNORECASE)]
    ok = not hits
    msgs = [] if ok else [f"Found placeholder marker(s): {', '.join(hits)}."]
    return _result(_CHECKS_BY_ID['no_placeholders'], ok, msgs, {"hits": hits})

@register_check(
    "artifacts_present",
    "Pilot artifacts are discoverable",
    "Ensure pilot artifacts are included (files exist on disk) and passed to the QA runner for verification.",
)
def check_artifacts_present(report_text: str, artifacts: Dict[str, Any]) -> Dict[str, Any]:
    paths = _artifact_paths(artifacts)
    missing = [str(p) for p in paths if not p.exists()]
    ok = bool(paths) and not missing
    msgs: List[str] = []
    if not paths:
        msgs.append("No artifact paths provided.")
    if missing:
        msgs.append(f"{len(missing)} artifact path(s) do not exist.")
    return _result(_CHECKS_BY_ID['artifacts_present'], ok, msgs, {"artifact_count": len(paths), "missing_paths": missing})

@register_check(
    "artifacts_referenced",
    "Artifacts are referenced in the report",
    "Reference pilot artifact filenames (or stable IDs) in DRAFT_REPORT_v0.md where relevant (methods, findings, appendix).",
    severity="warning",
)
def check_artifacts_referenced(report_text: str, artifacts: Dict[str, Any]) -> Dict[str, Any]:
    text = report_text or ""
    paths = _artifact_paths(artifacts)
    names = [p.name for p in paths]
    referenced = [n for n in names if n and n in text]
    ok = (not names) or (len(referenced) >= max(1, min(3, len(names))))
    msgs = [] if ok else [f"Only {len(referenced)}/{len(names)} artifact filenames referenced in report."]
    return _result(_CHECKS_BY_ID['artifacts_referenced'], ok, msgs, {"referenced": referenced})

@register_check(
    "json_artifacts_parse",
    "JSON artifacts parse cleanly (if any)",
    "Fix invalid JSON pilot artifacts, or exclude non-JSON files from JSON parsing inputs.",
    severity="warning",
)
def check_json_artifacts_parse(report_text: str, artifacts: Dict[str, Any]) -> Dict[str, Any]:
    bad: List[Dict[str, Any]] = []
    for p in _artifact_paths(artifacts):
        if p.suffix.lower() == ".json" and p.exists() and p.is_file():
            try:
                json.loads(p.read_text(encoding="utf-8"))
            except Exception as e:
                bad.append({"path": str(p), "error": f"{type(e).__name__}: {e}"})
    ok = not bad
    msgs = [] if ok else [f"{len(bad)} JSON artifact(s) failed to parse."]
    return _result(_CHECKS_BY_ID['json_artifacts_parse'], ok, msgs, {"bad": bad})

def checks_catalog() -> List[Dict[str, Any]]:
    return [{"id": c.id, "name": c.name, "severity": c.severity, "remediation": c.remediation} for c in _CHECKS]

def run_checks(report_text: str, artifacts: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    artifacts = artifacts or {}
    results: List[Dict[str, Any]] = []
    for c in _CHECKS:
        try:
            results.append(c.fn(report_text or "", artifacts))
        except Exception as e:
            results.append({
                "id": c.id,
                "name": c.name,
                "status": "fail",
                "messages": [f"Check crashed: {type(e).__name__}: {e}"],
                "remediation": c.remediation,
                "details": {"exception": type(e).__name__},
            })
    return results

# Build lookup after registration
_CHECKS_BY_ID = {c.id: c for c in _CHECKS}
