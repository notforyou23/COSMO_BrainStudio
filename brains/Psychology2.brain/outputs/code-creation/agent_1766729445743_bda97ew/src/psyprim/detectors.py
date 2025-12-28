"""Lightweight detectors for primary-source scholarship signals.

Focus: (1) edition/translation provenance, (2) variant pagination heuristics,
(3) repository citation/identifier extraction.

All functions are regex-based and intentionally lightweight for CLI use.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple, Iterable

_WS = r"[\s\u00A0]+"  # include non-breaking space
ROMAN = r"(?i:[ivxlcdm]+)"

def _norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def _finditer(pattern: str, text: str, flags: int = 0) -> Iterable[re.Match]:
    return re.finditer(pattern, text, flags)

def _collect(pattern: str, text: str, kind: str, flags: int = re.IGNORECASE) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for m in _finditer(pattern, text, flags):
        out.append({"type": kind, "match": _norm_space(m.group(0)), "span": [m.start(), m.end()], "groups": {k: v for k, v in m.groupdict().items() if v}})
    return out

def detect_edition_translation_provenance(text: str) -> List[Dict[str, Any]]:
    """Extract signals that a citation/text references a specific edition/translation/reprint/original."""
    t = text or ""
    signals: List[Dict[str, Any]] = []
    # Edition/revision
    signals += _collect(r"\b(?P<num>\d{1,2})(?:st|nd|rd|th)" + _WS + r"ed\.?\b", t, "edition")
    signals += _collect(r"\b(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)" + _WS + r"ed(?:ition)?\.?\b", t, "edition")
    signals += _collect(r"\b(?:rev\.?|revised|expanded|annotated|critical)" + _WS + r"ed(?:ition)?\.?\b", t, "edition")
    signals += _collect(r"\b(?:new|updated)" + _WS + r"ed(?:ition)?\.?\b", t, "edition")
    # Translation provenance
    signals += _collect(r"\b(?:trans\.?|translated)" + _WS + r"(?:by" + _WS + r"(?P<by>[^\.;\n\r\)]{2,80}))", t, "translation")
    signals += _collect(r"\btranslation" + _WS + r"of\b" + _WS + r"(?P<of>[^\.;\n\r\)]{2,120})", t, "translation")
    signals += _collect(r"\bfrom" + _WS + r"the" + _WS + r"(?P<lang>German|French|Italian|Spanish|Latin|Greek|Russian|Japanese|Chinese)" + _WS + r"(?:original|edition|text)\b", t, "translation")
    signals += _collect(r"\b(?P<lang>German|French|Italian|Spanish|Latin|Greek|Russian)" + _WS + r"ed\.?\b", t, "edition")
    # Original publication cues
    signals += _collect(r"\b(?:orig\.?" + _WS + r"pub\.?|originally" + _WS + r"published|first" + _WS + r"published)\b[^\n\r]{0,80}?\b(?P<year>1[6-9]\d{2}|20\d{2})\b", t, "original_pub")
    signals += _collect(r"\b\[(?P<year>1[6-9]\d{2}|20\d{2})\]\b", t, "bracket_year")
    # Reprint/collected works
    signals += _collect(r"\b(?:reprint(?:ed)?|facsimile|photographic" + _WS + r"reprint)\b", t, "reprint")
    signals += _collect(r"\b(?:collected" + _WS + r"works|complete" + _WS + r"works|gesammelte" + _WS + r"werke)\b", t, "collected")
    # De-dup by span
    seen = set()
    uniq: List[Dict[str, Any]] = []
    for s in signals:
        key = (s["type"], tuple(s["span"]))
        if key not in seen:
            seen.add(key)
            uniq.append(s)
    return sorted(uniq, key=lambda d: (d["span"][0], d["span"][1]))

def detect_variant_pagination(text: str) -> List[Dict[str, Any]]:
    """Heuristics for pagination variants (roman/arabic, bracketed pages, dual schemes, unpaginated)."""
    t = text or ""
    out: List[Dict[str, Any]] = []
    # Basic page/pp patterns incl roman numerals and bracketed
    out += _collect(r"\bpp?\.?" + _WS + r"(?P<pages>\[?\d+\]?)(?:\s*[-–—]\s*(?P<end>\[?\d+\]?))?\b", t, "page_ref")
    out += _collect(r"\bpp?\.?" + _WS + r"(?P<pages>\[?" + ROMAN + r"\]?)(?:\s*[-–—]\s*(?P<end>\[?" + ROMAN + r"\]?))?\b", t, "page_ref_roman")
    out += _collect(r"\b(?:at" + _WS + r"p\.?|p\.?)(?:" + _WS + r"at)?" + _WS + r"(?P<page>\[?\d+\]?|\[?" + ROMAN + r"\]?)\b", t, "page_ref")
    # Variant cues
    out += _collect(r"\b(?:pagination" + _WS + r"(?:varies|differs)|variously" + _WS + r"paginated|different" + _WS + r"pagination|original" + _WS + r"pagination)\b", t, "pagination_variant")
    out += _collect(r"\b(?:unpaginated|no" + _WS + r"pagination|without" + _WS + r"page" + _WS + r"numbers)\b", t, "unpaginated")
    out += _collect(r"\b(?:folio|ff\.?|leaf|leaves)\b", t, "folio")
    # Dual scheme hint: two page refs within short window separated by ; or / or "="
    for m in re.finditer(r"(pp?\.?[^\n\r]{0,60}?)(?:\s*[;/=]\s*)(pp?\.?[^\n\r]{0,60}?)", t, re.IGNORECASE):
        out.append({"type": "dual_pagination", "match": _norm_space(m.group(0)), "span": [m.start(), m.end()], "groups": {}})
    # Compact dedup
    seen = set()
    uniq: List[Dict[str, Any]] = []
    for s in out:
        key = (s["type"], tuple(s["span"]))
        if key not in seen:
            seen.add(key)
            uniq.append(s)
    return sorted(uniq, key=lambda d: (d["span"][0], d["span"][1]))

def detect_repository_citations(text: str) -> List[Dict[str, Any]]:
    """Extract repository/identifier mentions (DOI/ISBN/OCLC/ARK/Handle + common repository URLs)."""
    t = text or ""
    out: List[Dict[str, Any]] = []
    # Identifiers
    out += _collect(r"\bdoi\s*:\s*(?P<doi>10\.\d{4,9}/[^\s\]\)\>;\"']+)", t, "doi")
    out += _collect(r"\b(?:https?://(?:dx\.)?doi\.org/)(?P<doi>10\.\d{4,9}/[^\s\]\)\>;\"']+)", t, "doi_url")
    out += _collect(r"\bISBN\s*:?" + _WS + r"(?P<isbn>(?:97[89][- ]?)?[0-9][- 0-9]{8,16}[0-9Xx])\b", t, "isbn")
    out += _collect(r"\bOCLC\s*:?" + _WS + r"(?P<oclc>\d{5,12})\b", t, "oclc")
    out += _collect(r"\b(?:ARK\s*:?" + _WS + r"|ark:/)(?P<ark>ark:/\d{5,}/[A-Za-z0-9./_-]+)", t, "ark")
    out += _collect(r"\b(?:hdl\s*:?" + _WS + r"|handle\s*:?" + _WS + r"|https?://hdl\.handle\.net/)(?P<handle>\d{4,}/[A-Za-z0-9._-]+)", t, "handle")
    # Repository / source URLs (lightweight)
    repos = {
        "internet_archive": r"https?://archive\.org/(?:details|stream|download)/[^\s\]\)\>;\"']+",
        "hathitrust": r"https?://hdl\.handle\.net/2027/[^\s\]\)\>;\"']+|https?://babel\.hathitrust\.org/cgi/pt\?id=[^\s\]\)\>;\"']+",
        "worldcat": r"https?://www\.worldcat\.org/(?:oclc|title)/[^\s\]\)\>;\"']+",
        "google_books": r"https?://books\.google\.[^/]+/books\?id=[^\s\]\)\>;\"']+",
        "jstor": r"https?://www\.jstor\.org/(?:stable|stable/pdf)/[^\s\]\)\>;\"']+",
        "loc": r"https?://lccn\.loc\.gov/\d{8,12}|https?://www\.loc\.gov/item/[^\s\]\)\>;\"']+",
        "gutenberg": r"https?://www\.gutenberg\.org/ebooks/\d+",
    }
    for kind, pat in repos.items():
        for m in re.finditer(pat, t, re.IGNORECASE):
            out.append({"type": "repository_url", "subtype": kind, "match": m.group(0), "span": [m.start(), m.end()], "groups": {}})
    # Repository-style citations without URLs
    out += _collect(r"\b(?:Internet" + _WS + r"Archive|HathiTrust|WorldCat|Google" + _WS + r"Books|JSTOR|Library" + _WS + r"of" + _WS + r"Congress)\b", t, "repository_name")
    # Dedup
    seen = set()
    uniq: List[Dict[str, Any]] = []
    for s in out:
        key = (s.get("type"), s.get("subtype"), tuple(s["span"]))
        if key not in seen:
            seen.add(key)
            uniq.append(s)
    return sorted(uniq, key=lambda d: (d["span"][0], d["span"][1]))

def detect_primary_source_signals(text: str) -> Dict[str, Any]:
    """Convenience wrapper returning all detectors' outputs."""
    return {
        "edition_translation": detect_edition_translation_provenance(text),
        "variant_pagination": detect_variant_pagination(text),
        "repository_citations": detect_repository_citations(text),
    }
