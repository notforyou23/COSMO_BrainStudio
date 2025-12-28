"""Deterministic policy constraint checks for retrieve-then-verify.

This module is intentionally dependency-light and tolerant of either dict-style
or attribute-style input objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlparse
import re


@dataclass(frozen=True)
class ConstraintFailure:
    claim_id: str
    code: str
    message: str
    evidence_ref: Optional[str] = None


DEFAULT_THRESHOLDS: Dict[str, Any] = {
    "min_passages_per_claim": 1,
    "min_quotes_per_claim": 1,
    "min_total_quote_chars": 24,
    "min_unique_passage_ids_in_quotes": 1,
    "require_quote_in_passage_text": True,
    "max_quote_len": 2000,
}


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _claim_id(claim: Any) -> str:
    return str(_get(claim, "claim_id", _get(claim, "id", _get(claim, "uid", "UNKNOWN"))))


def _is_http_url(u: str) -> bool:
    try:
        p = urlparse(u)
    except Exception:
        return False
    return p.scheme in ("http", "https") and bool(p.netloc)


_WS_RE = re.compile(r"\s+")
def _norm(s: str) -> str:
    return _WS_RE.sub(" ", (s or "").strip())


def _iter_seq(x: Any) -> List[Any]:
    if x is None:
        return []
    if isinstance(x, (list, tuple)):
        return list(x)
    return [x]


def validate_claim_constraints(
    claim: Any,
    thresholds: Optional[Dict[str, Any]] = None,
) -> List[ConstraintFailure]:
    """Validate a single decomposed claim and return deterministic failures."""
    t = dict(DEFAULT_THRESHOLDS)
    if thresholds:
        t.update(thresholds)
    cid = _claim_id(claim)
    failures: List[ConstraintFailure] = []

    passages = _iter_seq(_get(claim, "passages", _get(claim, "retrieved_passages")))
    quotes = _iter_seq(_get(claim, "quotes", _get(claim, "evidence_quotes")))

    if len(passages) < int(t["min_passages_per_claim"]):
        failures.append(ConstraintFailure(cid, "NO_PASSAGES", "No retrieved passages attached to claim."))

    if len(quotes) < int(t["min_quotes_per_claim"]):
        failures.append(ConstraintFailure(cid, "NO_QUOTES", "No evidence quotes attached to claim."))

    pid_to_text: Dict[str, str] = {}
    for p in passages:
        pid = str(_get(p, "passage_id", _get(p, "id", _get(p, "uid", ""))) or "")
        text = str(_get(p, "text", _get(p, "content", "")) or "")
        if pid:
            pid_to_text[pid] = text

        prov = _get(p, "provenance", None)
        if prov is None:
            prov = {k: _get(p, k, None) for k in ("source_url", "url", "source_id", "doc_id")}
        src_url = _get(prov, "source_url", _get(prov, "url"))
        src_id = _get(prov, "source_id", _get(prov, "doc_id"))
        if src_url:
            if not _is_http_url(str(src_url)):
                failures.append(
                    ConstraintFailure(cid, "BAD_PROVENANCE_URL", f"Invalid source_url for passage {pid or '?'}", evidence_ref=pid or None)
                )
        elif not src_id:
            failures.append(
                ConstraintFailure(cid, "MISSING_PROVENANCE", f"Missing provenance for passage {pid or '?'}", evidence_ref=pid or None)
            )

    total_qchars = 0
    quote_pids: List[str] = []
    for i, q in enumerate(quotes):
        qtext = str(_get(q, "text", _get(q, "quote", "")) or "")
        qtext_n = _norm(qtext)
        if not qtext_n:
            failures.append(ConstraintFailure(cid, "EMPTY_QUOTE", f"Quote {i} has empty text."))
            continue
        if len(qtext_n) > int(t["max_quote_len"]):
            failures.append(ConstraintFailure(cid, "QUOTE_TOO_LONG", f"Quote {i} exceeds max length.", evidence_ref=str(len(qtext_n))))
        total_qchars += len(qtext_n)

        qpid = str(_get(q, "passage_id", _get(q, "source_passage_id", _get(q, "passage", ""))) or "")
        if not qpid:
            failures.append(ConstraintFailure(cid, "QUOTE_MISSING_PASSAGE_ID", f"Quote {i} missing passage_id."))
        else:
            quote_pids.append(qpid)
            if qpid not in pid_to_text:
                failures.append(
                    ConstraintFailure(cid, "QUOTE_BAD_PASSAGE_ID", f"Quote {i} references unknown passage_id {qpid}.", evidence_ref=qpid)
                )
            elif bool(t["require_quote_in_passage_text"]):
                ptxt = _norm(pid_to_text.get(qpid, ""))
                if qtext_n and ptxt and (qtext_n not in ptxt):
                    failures.append(
                        ConstraintFailure(cid, "QUOTE_NOT_IN_PASSAGE", f"Quote {i} not found verbatim in passage text.", evidence_ref=qpid)
                    )

    if quotes and total_qchars < int(t["min_total_quote_chars"]):
        failures.append(
            ConstraintFailure(cid, "INSUFFICIENT_QUOTE_TEXT", "Total quote text too short.", evidence_ref=str(total_qchars))
        )

    uniq_pids = {p for p in quote_pids if p}
    if quotes and len(uniq_pids) < int(t["min_unique_passage_ids_in_quotes"]):
        failures.append(
            ConstraintFailure(cid, "INSUFFICIENT_QUOTE_DIVERSITY", "Quotes do not cover enough distinct passages.", evidence_ref=str(len(uniq_pids)))
        )

    return failures


def validate_all_constraints(
    claims: Sequence[Any],
    thresholds: Optional[Dict[str, Any]] = None,
) -> Tuple[List[ConstraintFailure], Dict[str, List[ConstraintFailure]]]:
    """Validate a list of claims; returns (all_failures, failures_by_claim_id)."""
    all_failures: List[ConstraintFailure] = []
    by_claim: Dict[str, List[ConstraintFailure]] = {}
    for c in (claims or []):
        fs = validate_claim_constraints(c, thresholds=thresholds)
        if fs:
            cid = _claim_id(c)
            by_claim.setdefault(cid, []).extend(fs)
            all_failures.extend(fs)
    return all_failures, by_claim
