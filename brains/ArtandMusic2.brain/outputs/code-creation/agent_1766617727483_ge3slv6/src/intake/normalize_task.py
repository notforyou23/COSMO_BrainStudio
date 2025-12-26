from __future__ import annotations

from copy import deepcopy
import re
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_DATE_RANGE = {"start": "2019-01-01", "end": "2025-12-31"}


def _as_dict(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _clean_str(x: Any) -> Optional[str]:
    if x is None:
        return None
    if not isinstance(x, str):
        x = str(x)
    s = x.strip()
    return s or None


def _get_in(d: Dict[str, Any], path: Tuple[str, ...]) -> Any:
    cur: Any = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def _set_in(d: Dict[str, Any], path: Tuple[str, ...], value: Any) -> None:
    cur = d
    for k in path[:-1]:
        nxt = cur.get(k)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[k] = nxt
        cur = nxt
    cur[path[-1]] = value


def _ensure_date_range(task: Dict[str, Any]) -> None:
    # Prefer placing/maintaining date_range under query; mirror to top-level if missing.
    q = _as_dict(task.get("query"))
    task["query"] = q
    dr = _as_dict(q.get("date_range")) or _as_dict(task.get("date_range"))
    start = _clean_str(dr.get("start")) or DEFAULT_DATE_RANGE["start"]
    end = _clean_str(dr.get("end")) or DEFAULT_DATE_RANGE["end"]
    q["date_range"] = {"start": start, "end": end}
    if not isinstance(task.get("date_range"), dict):
        task["date_range"] = {"start": start, "end": end}


_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-']{2,}")


def _keywords_from_text(text: str, max_keywords: int = 10) -> List[str]:
    toks = [t.lower() for t in _WORD_RE.findall(text or "")]
    stop = {
        "the", "and", "for", "with", "that", "this", "from", "are", "was", "were", "has", "have",
        "had", "not", "but", "you", "your", "their", "they", "them", "his", "her", "she", "him",
        "its", "into", "over", "under", "than", "then", "when", "what", "which", "who", "whom",
        "why", "how", "a", "an", "to", "of", "in", "on", "at", "by", "as", "is", "it", "be", "or",
    }
    out: List[str] = []
    seen = set()
    for t in toks:
        if t in stop or len(t) < 4:
            continue
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= max_keywords:
            break
    return out


def _normalize_claim(task: Dict[str, Any]) -> None:
    claim = task.get("claim")
    if isinstance(claim, str):
        task["claim"] = {"verbatim": _clean_str(claim)}
        return
    c = _as_dict(claim)
    if not c:
        task["claim"] = c
        return
    if "verbatim" in c:
        c["verbatim"] = _clean_str(c.get("verbatim"))
    if "topic" in c:
        c["topic"] = _clean_str(c.get("topic"))
    task["claim"] = c


def _normalize_source(task: Dict[str, Any]) -> None:
    src = task.get("source")
    if isinstance(src, str):
        task["source"] = {"context": _clean_str(src)}
        return
    s = _as_dict(src)
    if not s:
        task["source"] = s
        return
    for k in ("context", "url", "title", "publisher", "outlet", "doi"):
        if k in s:
            s[k] = _clean_str(s.get(k))
    # Normalize author(s)
    if "author" in s and "authors" not in s:
        a = _clean_str(s.get("author"))
        if a:
            s["authors"] = [a]
    if "authors" in s:
        if isinstance(s["authors"], str):
            s["authors"] = [x.strip() for x in s["authors"].split(",") if x.strip()]
        elif isinstance(s["authors"], list):
            s["authors"] = [x for x in (_clean_str(v) for v in s["authors"]) if x]
        else:
            s["authors"] = []
    task["source"] = s


def _normalize_provenance(task: Dict[str, Any]) -> None:
    prov = task.get("provenance")
    if isinstance(prov, str):
        task["provenance"] = {"anchor": _clean_str(prov)}
        return
    p = _as_dict(prov)
    if not p:
        task["provenance"] = p
        return
    if "anchor" in p:
        p["anchor"] = _clean_str(p.get("anchor"))
    if "received_at" in p:
        p["received_at"] = _clean_str(p.get("received_at"))
    task["provenance"] = p


def _has_doi(task: Dict[str, Any]) -> bool:
    for path in (("doi",), ("source", "doi"), ("query", "doi")):
        v = _clean_str(_get_in(task, path))
        if v:
            return True
    return False


def _ensure_query_fields_if_no_doi(task: Dict[str, Any]) -> None:
    if _has_doi(task):
        return
    q = _as_dict(task.get("query"))
    task["query"] = q

    # Keywords: prefer explicit; else derive from verbatim claim.
    kws = q.get("keywords")
    if isinstance(kws, str):
        kws = [x.strip() for x in kws.split(",") if x.strip()]
    if not isinstance(kws, list):
        kws = []
    kws = [x for x in (_clean_str(v) for v in kws) if x]
    if not kws:
        verb = _clean_str(_get_in(task, ("claim", "verbatim"))) or ""
        kws = _keywords_from_text(verb)
    q["keywords"] = kws

    # Authors: prefer explicit; else use source authors if present.
    auth = q.get("authors")
    if isinstance(auth, str):
        auth = [x.strip() for x in auth.split(",") if x.strip()]
    if not isinstance(auth, list):
        auth = []
    auth = [x for x in (_clean_str(v) for v in auth) if x]
    if not auth:
        src_auth = _get_in(task, ("source", "authors"))
        if isinstance(src_auth, list):
            auth = [x for x in (_clean_str(v) for v in src_auth) if x]
    q["authors"] = auth

    # Optional helpful defaults (non-blocking)
    if "language" not in q:
        q["language"] = "en"


def normalize_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize an intake task by filling defaults and deriving query fields pre-validation."""
    t: Dict[str, Any] = deepcopy(task) if isinstance(task, dict) else {}
    _normalize_claim(t)
    _normalize_source(t)
    _normalize_provenance(t)
    _ensure_date_range(t)
    _ensure_query_fields_if_no_doi(t)
    return t
