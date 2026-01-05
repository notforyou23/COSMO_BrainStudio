from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


_DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.I)
_WS_RE = re.compile(r"\s+")
_SCHEME_RE = re.compile(r"^https?://", re.I)


def _norm_ws(s: str) -> str:
    return _WS_RE.sub(" ", s).strip()


def normalize_source_ref(ref: str) -> str:
    r = (ref or "").strip()
    if not r:
        return ""
    m = _DOI_RE.search(r)
    if m:
        return "doi:" + m.group(0).lower()
    r = r.strip()
    if not _SCHEME_RE.search(r):
        # allow bare domains or doi: forms; keep deterministic normalization
        if r.lower().startswith("doi:"):
            return "doi:" + r.split(":", 1)[1].strip().lower()
        r = "https://" + r
    return r


@dataclass(frozen=True, order=True)
class Span:
    start: int
    end: int  # python slice end (exclusive)

    def validate(self, text_len: int) -> List[str]:
        errs: List[str] = []
        if self.start < 0 or self.end < 0:
            errs.append("span indices must be non-negative")
        if self.end < self.start:
            errs.append("span end must be >= start")
        if self.end > text_len:
            errs.append("span end out of bounds")
        return errs


@dataclass(frozen=True)
class Citation:
    quote: str
    source: str  # url or doi or mixed string
    span: Span
    source_id: Optional[str] = None  # stable id for retrieved passage/document
    passage_span: Optional[Span] = None  # optional alignment into passage text

    def normalized_source(self) -> str:
        return normalize_source_ref(self.source)

    def validate_basic(self, answer_text: str) -> List[str]:
        errs: List[str] = []
        if not _norm_ws(self.quote):
            errs.append("empty quote")
        if not self.normalized_source():
            errs.append("empty source ref (url/doi)")
        errs.extend(self.span.validate(len(answer_text)))
        return errs


def _safe_slice(s: str, sp: Span) -> str:
    return s[sp.start : sp.end]


def validate_citations(
    answer_text: str,
    citations: Sequence[Citation],
    *,
    passages: Optional[Mapping[str, Mapping[str, Any]]] = None,
    require_quote_in_answer_span: bool = True,
    require_quote_in_passage: bool = True,
) -> List[str]:
    """Deterministic validators for must-cite constraints.

    passages: mapping of source_id -> {text: str, url/doi/source: str}
    """
    errs: List[str] = []
    passages = passages or {}

    seen: set = set()
    for i, c in enumerate(citations or []):
        pfx = f"citation[{i}]"
        errs.extend(f"{pfx}: {e}" for e in c.validate_basic(answer_text))

        key = (c.span.start, c.span.end, _norm_ws(c.quote), c.normalized_source(), c.source_id)
        if key in seen:
            errs.append(f"{pfx}: duplicate citation")
        seen.add(key)

        if require_quote_in_answer_span and not c.span.validate(len(answer_text)):
            got = _norm_ws(_safe_slice(answer_text, c.span))
            want = _norm_ws(c.quote)
            if got != want:
                errs.append(f"{pfx}: answer span text does not exactly match quote after ws-normalization")

        if c.source_id is not None and c.source_id in passages:
            meta = passages[c.source_id]
            ptext = str(meta.get("text", "") or "")
            psrc = normalize_source_ref(str(meta.get("source") or meta.get("url") or meta.get("doi") or ""))
            if psrc and c.normalized_source() and psrc != c.normalized_source():
                errs.append(f"{pfx}: source ref does not match passage provenance")
            if require_quote_in_passage and _norm_ws(c.quote) and ptext:
                qn = _norm_ws(c.quote)
                pn = _norm_ws(ptext)
                if qn not in pn:
                    errs.append(f"{pfx}: quote not found in passage text after ws-normalization")
            if c.passage_span is not None and ptext:
                errs.extend(f"{pfx}: {e}" for e in c.passage_span.validate(len(ptext)))
                if not c.passage_span.validate(len(ptext)):
                    gotp = _norm_ws(_safe_slice(ptext, c.passage_span))
                    want = _norm_ws(c.quote)
                    if gotp != want:
                        errs.append(f"{pfx}: passage_span text does not match quote after ws-normalization")
        elif c.source_id is not None and require_quote_in_passage:
            errs.append(f"{pfx}: unknown source_id; cannot verify against passage")

    return errs


def enforce_must_cite(
    answer_text: str,
    citations: Sequence[Citation],
    *,
    passages: Optional[Mapping[str, Mapping[str, Any]]] = None,
) -> None:
    errs = validate_citations(answer_text, citations, passages=passages)
    if errs:
        raise ValueError("must-cite validation failed: " + "; ".join(errs))


def citations_from_dicts(items: Iterable[Mapping[str, Any]]) -> List[Citation]:
    out: List[Citation] = []
    for it in items or []:
        sp = it.get("span") or {}
        psp = it.get("passage_span")
        out.append(
            Citation(
                quote=str(it.get("quote") or ""),
                source=str(it.get("source") or it.get("url") or it.get("doi") or ""),
                span=Span(int(sp.get("start", -1)), int(sp.get("end", -1))),
                source_id=(str(it["source_id"]) if "source_id" in it and it["source_id"] is not None else None),
                passage_span=(
                    Span(int(psp.get("start", -1)), int(psp.get("end", -1))) if isinstance(psp, Mapping) else None
                ),
            )
        )
    return out
