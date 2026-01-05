from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Union


@dataclass(frozen=True)
class Passage:
    passage_id: str
    text: str
    url: Optional[str] = None
    doi: Optional[str] = None
    title: Optional[str] = None


@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    failures: List[Dict[str, Any]]
    checked: int


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    s = s.replace("\u201c", '"').replace("\u201d", '"').replace("\u2018", "'").replace("\u2019", "'")
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r"\n+", "\n", s)
    return s.strip()


def _norm_for_contains(s: str) -> str:
    s = _norm(s)
    s = re.sub(r"\s+", " ", s)
    return s


def _has_provenance(p: Passage) -> bool:
    url = (p.url or "").strip()
    doi = (p.doi or "").strip()
    return bool(url) or bool(doi)


class Verifier:
    """
    Enforces explicit must-cite constraints over an answer given retrieved passages.

    For each citation:
      - quote (string) must be present
      - passage_id must map to a retrieved passage
      - span must be provided as [start, end) (list/tuple) or {"start":..,"end":..}
      - passage must include provenance: url and/or doi (configurable)
      - quote must equal passage.text[span] after normalization
      - quote must also appear in the answer (configurable)
    """

    def __init__(self, require_quote_in_answer: bool = True, require_provenance: bool = True):
        self.require_quote_in_answer = require_quote_in_answer
        self.require_provenance = require_provenance

    def verify(
        self,
        answer: str,
        citations: Sequence[Any],
        passages: Union[Sequence[Any], Dict[str, Any]],
    ) -> VerificationResult:
        ans_norm = _norm_for_contains(answer)
        pmap: Dict[str, Passage] = {}

        items = passages.values() if isinstance(passages, dict) else passages
        for p in items or []:
            pid = str(_get(p, "passage_id", _get(p, "id", ""))).strip()
            if not pid:
                continue
            pmap[pid] = Passage(
                passage_id=pid,
                text=str(_get(p, "text", "")),
                url=_get(p, "url", None),
                doi=_get(p, "doi", None),
                title=_get(p, "title", None),
            )

        failures: List[Dict[str, Any]] = []
        for i, c in enumerate(citations or []):
            quote = str(_get(c, "quote", "") or "")
            pid = str(_get(c, "passage_id", _get(c, "passageId", "")) or "").strip()
            span = _get(c, "span", None)

            if isinstance(span, dict):
                start, end = span.get("start", None), span.get("end", None)
            elif isinstance(span, (list, tuple)) and len(span) == 2:
                start, end = span[0], span[1]
            else:
                start, end = None, None

            cfail: Dict[str, Any] = {"index": i, "passage_id": pid, "quote": quote}

            if not quote.strip():
                cfail["error"] = "missing_quote"
                failures.append(cfail)
                continue
            if not pid or pid not in pmap:
                cfail["error"] = "missing_or_unknown_passage_id"
                failures.append(cfail)
                continue

            p = pmap[pid]
            if self.require_provenance and not _has_provenance(p):
                cfail["error"] = "missing_provenance_url_or_doi"
                failures.append(cfail)
                continue

            if start is None or end is None:
                cfail["error"] = "missing_span"
                failures.append(cfail)
                continue
            try:
                start_i, end_i = int(start), int(end)
            except Exception:
                cfail["error"] = "non_integer_span"
                failures.append(cfail)
                continue
            if start_i < 0 or end_i <= start_i or end_i > len(p.text):
                cfail["error"] = "span_out_of_bounds"
                cfail["passage_len"] = len(p.text)
                cfail["span"] = [start_i, end_i]
                failures.append(cfail)
                continue

            passage_slice = p.text[start_i:end_i]
            if _norm(passage_slice) != _norm(quote):
                cfail["error"] = "span_quote_mismatch"
                cfail["span"] = [start_i, end_i]
                cfail["passage_slice"] = passage_slice
                failures.append(cfail)
                continue

            if self.require_quote_in_answer and _norm_for_contains(quote) not in ans_norm:
                cfail["error"] = "quote_not_in_answer"
                failures.append(cfail)
                continue

        return VerificationResult(ok=(len(failures) == 0), failures=failures, checked=len(citations or []))
