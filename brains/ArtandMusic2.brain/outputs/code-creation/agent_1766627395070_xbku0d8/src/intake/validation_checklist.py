from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_DATE_RANGE = {"start": "2019-01-01", "end": "2025-12-31"}


def _get(d: Any, path: str) -> Any:
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _is_nonempty_str(x: Any) -> bool:
    return isinstance(x, str) and x.strip() != ""


def _as_list(x: Any) -> List[Any]:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]


def _has_any_nonempty_str(values: List[Any]) -> bool:
    for v in values:
        if _is_nonempty_str(v):
            return True
        if isinstance(v, dict):
            for vv in v.values():
                if _is_nonempty_str(vv):
                    return True
    return False


def _find_doi(task: Dict[str, Any]) -> Optional[str]:
    candidates = [
        _get(task, "doi"),
        _get(task, "identifiers.doi"),
        _get(task, "source.doi"),
        _get(task, "source.identifiers.doi"),
        _get(task, "document.doi"),
    ]
    for c in candidates:
        if _is_nonempty_str(c):
            return c.strip()
    return None


def normalize_for_checklist(task: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy with DOI-missing defaults applied (date range 2019–2025)."""
    t = deepcopy(task) if isinstance(task, dict) else {}
    doi = _find_doi(t)
    if not doi:
        q = t.get("query")
        if not isinstance(q, dict):
            q = {}
            t["query"] = q
        dr = q.get("date_range")
        if not isinstance(dr, dict):
            dr = {}
            q["date_range"] = dr
        if not _is_nonempty_str(dr.get("start")):
            dr["start"] = DEFAULT_DATE_RANGE["start"]
        if not _is_nonempty_str(dr.get("end")):
            dr["end"] = DEFAULT_DATE_RANGE["end"]
    return t


def validate_checklist(task: Dict[str, Any], *, apply_defaults: bool = True) -> Tuple[bool, List[Dict[str, Any]], Dict[str, Any]]:
    """Blocking checklist for intake. Returns (ok, errors, normalized_task)."""
    t = normalize_for_checklist(task) if apply_defaults else (deepcopy(task) if isinstance(task, dict) else {})
    errors: List[Dict[str, Any]] = []

    def add(code: str, path: str, message: str) -> None:
        errors.append({"severity": "blocking", "code": code, "path": path, "message": message})

    # 1) Verbatim claim (minimum viable input)
    claim = _get(t, "claim") if isinstance(_get(t, "claim"), dict) else {}
    verbatim = _get(t, "claim.verbatim") or _get(t, "claim.text") or _get(t, "verbatim_claim")
    if not _is_nonempty_str(verbatim):
        add(
            "MISSING_VERBATIM_CLAIM",
            "claim.verbatim",
            "Missing verbatim claim text; provide the exact quoted claim (verbatim) to be verified.",
        )

    # 2) Source context (who/where/when + link/screenshot/citation)
    src = _get(t, "source") if isinstance(_get(t, "source"), dict) else {}
    src_context_ok = _has_any_nonempty_str(
        [
            src.get("url"),
            src.get("link"),
            src.get("citation"),
            src.get("title"),
            src.get("publisher"),
            src.get("publication"),
            src.get("published_at"),
            src.get("date"),
            src.get("author"),
            src.get("speaker"),
            _get(t, "context.url"),
            _get(t, "context.citation"),
            _get(t, "context.published_at"),
        ]
    )
    if not src_context_ok:
        add(
            "MISSING_SOURCE_CONTEXT",
            "source",
            "Missing source context; include who said it, where/what it appeared in, when, and a URL/citation/screenshot reference.",
        )

    # 3) Provenance anchor (stable identifier for where the claim/context is captured)
    prov_anchor = (
        _get(t, "provenance.anchor")
        or _get(t, "provenance.url")
        or _get(t, "provenance.uri")
        or _get(t, "provenance.snapshot_url")
        or _get(t, "provenance.web_archive_url")
        or _get(t, "evidence.anchor")
        or _get(t, "evidence.url")
    )
    if not _is_nonempty_str(prov_anchor):
        add(
            "MISSING_PROVENANCE_ANCHOR",
            "provenance.anchor",
            "Missing provenance anchor; provide a stable link/URI/snapshot/archive anchor tying the claim to its source context.",
        )

    # 4) DOI-missing conditional requirements: require query keywords and author fields; default date_range already applied
    doi = _find_doi(t)
    if not doi:
        q = _get(t, "query") if isinstance(_get(t, "query"), dict) else {}
        keywords = _as_list(q.get("keywords") or q.get("keyword") or q.get("terms"))
        authors = _as_list(q.get("authors") or q.get("author") or q.get("author_names"))
        if not _has_any_nonempty_str(keywords):
            add(
                "MISSING_QUERY_KEYWORDS",
                "query.keywords",
                "DOI is missing; provide query keywords/terms to enable retrieval (e.g., key phrases from the claim).",
            )
        if not _has_any_nonempty_str(authors):
            add(
                "MISSING_QUERY_AUTHORS",
                "query.authors",
                "DOI is missing; provide at least one author/speaker/organization name for the query.",
            )
        dr = q.get("date_range") if isinstance(q.get("date_range"), dict) else {}
        if not (_is_nonempty_str(dr.get("start")) and _is_nonempty_str(dr.get("end"))):
            add(
                "MISSING_DATE_RANGE",
                "query.date_range",
                "DOI is missing; a date_range is required (defaults 2019-01-01 to 2025-12-31 will be applied when absent).",
            )

    return (len(errors) == 0), errors, t
