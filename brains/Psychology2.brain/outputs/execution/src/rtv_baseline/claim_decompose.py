from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Sequence, Tuple


_WS_RE = re.compile(r"\s+")
_YEAR_RE = re.compile(r"\b(1[6-9]\d{2}|20\d{2}|2100)\b")
_ACCORDING_RE = re.compile(r"\baccording to\b\s+([^,.;]+)", re.I)
_IN_LOC_RE = re.compile(r"\b(in|at|near)\b\s+([A-Z][^,.;]+)$")
_MODAL_RE = re.compile(r"\b(may|might|could|can|should|would|will|must)\b", re.I)
_NEG_RE = re.compile(r"\b(not|never|no)\b", re.I)


@dataclass(frozen=True)
class AtomicClaim:
    """Smallest self-contained proposition with machine-readable fields."""

    id: str
    text: str
    subject: str
    predicate: str
    obj: str
    scope: Dict[str, Optional[str]]
    provenance: Dict[str, object]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def _norm_space(s: str) -> str:
    s = s.strip().strip('"\"“”')
    s = _WS_RE.sub(" ", s)
    return s


def _strip_leading_connective(s: str) -> str:
    s2 = re.sub(r"^(and|but|also|then|however|moreover)\b\s*", "", s, flags=re.I).strip()
    return s2 or s


def _protect_abbrev(text: str) -> str:
    # Prevent sentence split on common abbreviations.
    for ab in ["e.g.", "i.e.", "U.S.", "U.K.", "Dr.", "Mr.", "Ms.", "Prof."]:
        text = text.replace(ab, ab.replace(".", "<DOT>"))
    return text


def _unprotect_abbrev(text: str) -> str:
    return text.replace("<DOT>", ".")


def _split_into_units(claim: str) -> List[str]:
    c = _norm_space(claim)
    c = _protect_abbrev(c)

    # Split on sentence boundaries first.
    parts: List[str] = []
    for seg in re.split(r"(?<=[.!?])\s+", c):
        seg = seg.strip(" ;,")
        if seg:
            parts.append(seg)

    # Further split on high-level conjunctions; keep it conservative.
    units: List[str] = []
    for p in parts:
        # Avoid splitting inside parentheses by temporarily removing them.
        tmp = re.sub(r"\([^)]*\)", lambda m: m.group(0).replace(" and ", " <AND> ").replace(" or ", " <OR> "), p, flags=re.I)
        tmp2 = re.sub(r"\s+;\s+", " ; ", tmp)
        sub = re.split(r"\s+(?:;|and|but|or)\s+", tmp2, flags=re.I)
        for s in sub:
            s = s.replace("<AND>", " and ").replace("<OR>", " or ")
            s = _unprotect_abbrev(s)
            s = _strip_leading_connective(_norm_space(s.strip(" ;,")))
            if s:
                units.append(s)

    # Deduplicate while preserving order.
    seen = set()
    out = []
    for u in units:
        k = u.lower()
        if k not in seen:
            seen.add(k)
            out.append(u)
    return out


def _extract_scope(text: str) -> Dict[str, Optional[str]]:
    years = _YEAR_RE.findall(text)
    year = years[0] if years else None
    loc = None
    mloc = _IN_LOC_RE.search(text)
    if mloc:
        loc = _norm_space(mloc.group(2))
    modal = None
    mmod = _MODAL_RE.search(text)
    if mmod:
        modal = mmod.group(1).lower()
    negated = bool(_NEG_RE.search(text))
    return {"time": year, "location": loc, "modal": modal, "negated": "true" if negated else "false"}


def _extract_attribution(text: str) -> Optional[str]:
    m = _ACCORDING_RE.search(text)
    if m:
        return _norm_space(m.group(1))
    return None


def _parse_simple_svo(text: str) -> Tuple[str, str, str]:
    t = _norm_space(text)

    # Patterns are intentionally simple; fall back to whole-text predicate.
    patterns = [
        r"^(?P<sub>.+?)\s+(?P<pred>is|are|was|were|becomes|became|remains)\s+(?P<obj>.+)$",
        r"^(?P<sub>.+?)\s+(?P<pred>has|have|had)\s+(?P<obj>.+)$",
        r"^(?P<sub>.+?)\s+(?P<pred>won|wins|win|lost|loses|lose|led|leads|lead|killed|kills|kill|built|builds|build|founded|founds|found)\s+(?P<obj>.+)$",
        r"^(?P<sub>.+?)\s+(?P<pred>said|says|reported|reports|announced|announces|claimed|claims)\s+(?P<obj>.+)$",
    ]
    for pat in patterns:
        m = re.match(pat, t, flags=re.I)
        if m:
            sub = _norm_space(m.group("sub"))
            pred = m.group("pred").lower()
            obj = _norm_space(m.group("obj"))
            return sub, pred, obj

    # Fallback: treat first noun-like chunk as subject if possible.
    m2 = re.match(r"^(?P<sub>(?:the|a|an)?\s*[A-Z][^,;]+?)\s+(?P<rest>.+)$", t)
    if m2:
        return _norm_space(m2.group("sub")), "asserts", _norm_space(m2.group("rest"))
    return "UNKNOWN", "asserts", t


def decompose_claim(claim: str, *, claim_id_prefix: str = "c") -> List[Dict[str, object]]:
    """Decompose an input claim into atomic claims.

    Output fields are fixed and machine-readable:
      - subject, predicate, obj
      - scope: time/location/modal/negated
      - provenance: quote and attribution requirements for downstream verification
    """
    units = _split_into_units(claim)
    out: List[AtomicClaim] = []
    for i, u in enumerate(units, start=1):
        subj, pred, obj = _parse_simple_svo(u)
        scope = _extract_scope(u)
        attrib = _extract_attribution(u)
        prov = {
            "must_include_quote": True,
            "must_match_subject": True if subj != "UNKNOWN" else False,
            "attribution": attrib,
            "requires_primary_source": False,
        }
        out.append(
            AtomicClaim(
                id=f"{claim_id_prefix}{i}",
                text=u,
                subject=subj,
                predicate=pred,
                obj=obj,
                scope=scope,
                provenance=prov,
            )
        )
    return [a.to_dict() for a in out]


__all__ = ["AtomicClaim", "decompose_claim"]
