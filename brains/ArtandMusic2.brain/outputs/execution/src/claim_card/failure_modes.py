"""Canonical failure-mode codes + detection + aggregation utilities for Claim Card pilots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple
from collections import Counter, defaultdict


@dataclass(frozen=True)
class FailureMode:
    code: str
    title: str
    description: str
    severity: str = "error"


FAILURE_MODES: Dict[str, FailureMode] = {
    "MISSING_METADATA": FailureMode(
        "MISSING_METADATA",
        "Missing required metadata",
        "One or more mandatory metadata fields are absent or empty.",
        "error",
    ),
    "VERSION_AMBIGUITY": FailureMode(
        "VERSION_AMBIGUITY",
        "Version ambiguity",
        "Version fields are missing, inconsistent, or not parseable; cannot determine which version applies.",
        "error",
    ),
    "CORRECTION_HISTORY_MISSING": FailureMode(
        "CORRECTION_HISTORY_MISSING",
        "Missing correction history",
        "Corrections exist but are not recorded, or correctionHistory is required by policy but absent.",
        "warning",
    ),
    "CORRECTION_HISTORY_INVALID": FailureMode(
        "CORRECTION_HISTORY_INVALID",
        "Invalid correction history",
        "Correction history exists but entries are malformed (missing dates, ids, or change rationale).",
        "error",
    ),
    "PROVENANCE_MISSING": FailureMode(
        "PROVENANCE_MISSING",
        "Missing provenance/source",
        "Claim lacks traceable source, citation, or provenance metadata.",
        "error",
    ),
    "SCHEMA_VALIDATION_ERROR": FailureMode(
        "SCHEMA_VALIDATION_ERROR",
        "Schema validation error",
        "Schema validation failed; see details for specific paths and messages.",
        "error",
    ),
}


def make_issue(
    code: str,
    message: str,
    *,
    path: Optional[str] = None,
    severity: Optional[str] = None,
    claim_id: Optional[str] = None,
    evidence: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    fm = FAILURE_MODES.get(code)
    return {
        "code": code,
        "severity": severity or (fm.severity if fm else "error"),
        "message": message,
        "path": path,
        "claim_id": claim_id,
        "evidence": evidence or {},
    }


def _is_missing(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str) and not v.strip():
        return True
    if isinstance(v, (list, dict)) and len(v) == 0:
        return True
    return False


def _get(d: Dict[str, Any], key_path: str) -> Any:
    cur: Any = d
    for part in key_path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def detect_missing_metadata(
    card: Dict[str, Any],
    required_paths: Iterable[str],
    *,
    claim_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    for p in required_paths:
        v = _get(card, p)
        if _is_missing(v):
            issues.append(make_issue("MISSING_METADATA", f"Missing required field: {p}", path=p, claim_id=claim_id))
    return issues


def detect_provenance_missing(
    card: Dict[str, Any],
    provenance_paths: Iterable[str] = ("source", "provenance", "citations"),
    *,
    claim_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    for p in provenance_paths:
        if not _is_missing(_get(card, p)):
            return []
    return [make_issue("PROVENANCE_MISSING", "No source/provenance/citations provided.", path="provenance", claim_id=claim_id)]


def detect_version_ambiguity(
    card: Dict[str, Any],
    *,
    version_path: str = "version",
    schema_version_path: str = "schemaVersion",
    claim_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    v = _get(card, version_path)
    sv = _get(card, schema_version_path)
    if _is_missing(v) and _is_missing(sv):
        return [make_issue("VERSION_AMBIGUITY", "Both version and schemaVersion are missing.", path=version_path, claim_id=claim_id)]
    if isinstance(v, dict) or isinstance(sv, dict):
        return [make_issue("VERSION_AMBIGUITY", "Version fields must be scalar strings.", path=version_path, claim_id=claim_id)]
    if not _is_missing(v) and not isinstance(v, str):
        return [make_issue("VERSION_AMBIGUITY", "version is not a string.", path=version_path, claim_id=claim_id)]
    if not _is_missing(sv) and not isinstance(sv, str):
        return [make_issue("VERSION_AMBIGUITY", "schemaVersion is not a string.", path=schema_version_path, claim_id=claim_id)]
    if isinstance(v, str) and isinstance(sv, str) and v.strip() and sv.strip() and v.strip() == sv.strip():
        return []
    if _is_missing(v) or _is_missing(sv):
        return []
    return [make_issue("VERSION_AMBIGUITY", "version and schemaVersion disagree.", path=f"{version_path},{schema_version_path}", claim_id=claim_id, evidence={"version": v, "schemaVersion": sv})]


def detect_correction_history(
    card: Dict[str, Any],
    *,
    history_path: str = "correctionHistory",
    required_if_field: Optional[str] = "correctedFrom",
    claim_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    history = _get(card, history_path)
    corrected_from = _get(card, required_if_field) if required_if_field else None
    if _is_missing(history):
        if not _is_missing(corrected_from):
            issues.append(make_issue("CORRECTION_HISTORY_MISSING", f"{history_path} missing but {required_if_field} is present.", path=history_path, claim_id=claim_id))
        return issues
    if not isinstance(history, list):
        return [make_issue("CORRECTION_HISTORY_INVALID", f"{history_path} must be a list.", path=history_path, claim_id=claim_id)]
    for i, entry in enumerate(history):
        if not isinstance(entry, dict):
            issues.append(make_issue("CORRECTION_HISTORY_INVALID", "Correction entry must be an object.", path=f"{history_path}[{i}]", claim_id=claim_id))
            continue
        missing = [k for k in ("id", "timestamp", "summary") if _is_missing(entry.get(k))]
        if missing:
            issues.append(make_issue("CORRECTION_HISTORY_INVALID", f"Correction entry missing: {', '.join(missing)}", path=f"{history_path}[{i}]", claim_id=claim_id, evidence={"missing": missing}))
    return issues


def schema_errors_to_issues(
    errors: Iterable[Dict[str, Any]],
    *,
    claim_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for e in errors:
        msg = str(e.get("message") or e)
        path = e.get("path") or e.get("instancePath") or e.get("schema_path")
        out.append(make_issue("SCHEMA_VALIDATION_ERROR", msg, path=str(path) if path is not None else None, claim_id=claim_id, evidence={k: v for k, v in e.items() if k not in {"message", "path", "instancePath"}}))
    return out


def summarize_issues(issues: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    issues_l = list(issues)
    by_code = Counter(i.get("code") for i in issues_l)
    by_sev = Counter(i.get("severity") for i in issues_l)
    by_claim = defaultdict(Counter)
    for i in issues_l:
        cid = i.get("claim_id") or "(unknown)"
        by_claim[cid][i.get("code")] += 1
    return {
        "total": len(issues_l),
        "by_code": dict(sorted(by_code.items())),
        "by_severity": dict(sorted(by_sev.items())),
        "by_claim_id": {k: dict(sorted(v.items())) for k, v in sorted(by_claim.items())},
    }


def merge_issue_lists(*lists: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for lst in lists:
        out.extend(list(lst))
    return out
