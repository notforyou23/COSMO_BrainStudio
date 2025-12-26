"""Parser utilities for claim cards and case studies.

Claim cards are markdown documents containing labeled sections for required fields.
Case studies are markdown documents that reference claim card IDs for each empirical claim.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Dict, Iterable, List, Optional, Tuple


_VERIFICATION_ALLOWED = {"unverified", "partially", "verified"}
_EVIDENCE_TYPES = {
    "experiment",
    "observational",
    "survey",
    "simulation",
    "meta-analysis",
    "review",
    "theory",
    "expert opinion",
    "mixed",
    "unknown",
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _strip_md(s: str) -> str:
    s = s or ""
    s = re.sub(r"`([^`]*)`", r"\1", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
    s = re.sub(r"\*([^*]+)\*", r"\1", s)
    return s.strip()


def _split_list_lines(text: str) -> List[str]:
    items: List[str] = []
    for line in (text or "").splitlines():
        m = re.match(r"^\s*(?:[-*+]|\d+\.)\s+(.*)\s*$", line)
        if m:
            items.append(_strip_md(m.group(1)))
        elif line.strip():
            items.append(_strip_md(line.strip()))
    return [i for i in (_norm(x) for x in items) if i]


def _extract_urls_dois(text: str) -> Tuple[List[str], List[str]]:
    t = text or ""
    urls = re.findall(r"https?://[^\s)\]>]+", t)
    dois = re.findall(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b", t)
    return sorted(set(urls)), sorted(set(dois))


def _collect_heading_sections(md: str) -> Dict[str, str]:
    md = md or ""
    lines = md.splitlines()
    sections: Dict[str, List[str]] = {}
    current_key: Optional[str] = None
    buf: List[str] = []
    def flush():
        nonlocal current_key, buf
        if current_key is not None:
            sections.setdefault(current_key, [])
            sections[current_key].append("\n".join(buf).strip())
        buf = []
    for line in lines:
        h = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if h:
            flush()
            current_key = _norm(h.group(2)).lower()
            continue
        if current_key is not None:
            buf.append(line)
    flush()
    return {k: "\n\n".join(v).strip() for k, v in sections.items()}


def _get_first_match(sections: Dict[str, str], keys: Iterable[str]) -> str:
    for k in keys:
        for sk, sv in sections.items():
            if sk == k or sk.startswith(k + " ") or (k in sk and len(sk) <= len(k) + 8):
                if sv.strip():
                    return sv.strip()
    return ""


@dataclass(frozen=True)
class ClaimCard:
    claim_id: str
    claim_text: str
    scope: str
    evidence_type: str
    citations: List[str]
    urls: List[str]
    dois: List[str]
    verification_status: str
    abstention_triggers: List[str]


def parse_claim_card(markdown: str, *, default_id: str = "") -> Dict[str, object]:
    """Parse a claim card markdown into structured fields.

    Expected headings (case-insensitive, flexible):
      - Claim Card ID / ID
      - Claim Text / Claim
      - Scope
      - Evidence Type
      - Citations / References / Sources
      - Verification Status
      - Abstention Triggers
    """
    sections = _collect_heading_sections(markdown)
    cid = _norm(_strip_md(_get_first_match(sections, ["claim card id", "claim id", "id"]))) or _norm(default_id)
    claim_text = _norm(_strip_md(_get_first_match(sections, ["claim text", "claim"])))
    scope = _norm(_strip_md(_get_first_match(sections, ["scope"])))
    evidence_type = _norm(_strip_md(_get_first_match(sections, ["evidence type", "evidence"]))).lower() or "unknown"
    citations_raw = _get_first_match(sections, ["citations", "references", "sources"])
    citations = _split_list_lines(citations_raw) if citations_raw else []
    abst_raw = _get_first_match(sections, ["abstention triggers", "abstain triggers", "abstentions"])
    abstention_triggers = _split_list_lines(abst_raw) if abst_raw else []
    ver = _norm(_strip_md(_get_first_match(sections, ["verification status", "verification"]))).lower() or "unverified"

    urls1, dois1 = _extract_urls_dois("\n".join(citations))
    urls2, dois2 = _extract_urls_dois(markdown)
    urls = sorted(set(urls1 + urls2))
    dois = sorted(set(dois1 + dois2))

    if ver not in _VERIFICATION_ALLOWED:
        ver = "unverified"
    if evidence_type not in _EVIDENCE_TYPES:
        evidence_type = "unknown"

    return {
        "claim_id": cid,
        "claim_text": claim_text,
        "scope": scope,
        "evidence_type": evidence_type,
        "citations": citations,
        "urls": urls,
        "dois": dois,
        "verification_status": ver,
        "abstention_triggers": abstention_triggers,
    }


def parse_claim_card_typed(markdown: str, *, default_id: str = "") -> ClaimCard:
    d = parse_claim_card(markdown, default_id=default_id)
    return ClaimCard(
        claim_id=str(d.get("claim_id") or ""),
        claim_text=str(d.get("claim_text") or ""),
        scope=str(d.get("scope") or ""),
        evidence_type=str(d.get("evidence_type") or "unknown"),
        citations=list(d.get("citations") or []),
        urls=list(d.get("urls") or []),
        dois=list(d.get("dois") or []),
        verification_status=str(d.get("verification_status") or "unverified"),
        abstention_triggers=list(d.get("abstention_triggers") or []),
    )


_CLAIM_ID_PATTERNS = [
    re.compile(r"\bCC-[A-Za-z0-9_-]+\b"),
    re.compile(r"\bCLAIM-[A-Za-z0-9_-]+\b"),
]


def extract_empirical_claim_refs(case_study_markdown: str) -> List[str]:
    """Extract claim card IDs referenced in a case study markdown.

    Recognizes IDs like CC-001 or CLAIM-foo anywhere in text; also recognizes
    explicit link syntax like [CC-001](../claim_cards/CC-001.md).
    """
    text = case_study_markdown or ""
    found: List[str] = []
    for pat in _CLAIM_ID_PATTERNS:
        found.extend(pat.findall(text))
    return sorted(set(found))


def extract_empirical_claim_linkages(case_study_markdown: str) -> List[Dict[str, str]]:
    """Extract (empirical claim text -> claim card ID) linkages when available.

    Heuristic:
      - lines that contain an ID (CC-.../CLAIM-...) and also look like bullets/numbered items
        will be treated as an empirical claim statement.
    Returns list of dicts: {"claim_id": ..., "claim_line": ...}
    """
    text = case_study_markdown or ""
    out: List[Dict[str, str]] = []
    for line in text.splitlines():
        if not re.match(r"^\s*(?:[-*+]|\d+\.)\s+", line):
            continue
        ids = []
        for pat in _CLAIM_ID_PATTERNS:
            ids.extend(pat.findall(line))
        if not ids:
            continue
        clean = _norm(_strip_md(re.sub(r"\[[^\]]*\]\([^\)]*\)", "", line)))
        clean = re.sub(r"\b(?:" + "|".join(re.escape(i) for i in ids) + r")\b", "", clean)
        clean = _norm(clean).strip("-–—: ")
        for cid in sorted(set(ids)):
            out.append({"claim_id": cid, "claim_line": clean})
    # stable ordering
    out.sort(key=lambda d: (d.get("claim_id", ""), d.get("claim_line", "")))
    return out
