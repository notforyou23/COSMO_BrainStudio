"""Claim card tooling: schema-light parsing + validation for empirical-claim workflow.

This package provides utilities to:
- Parse claim-card markdown into structured fields.
- Validate required fields and allowed values.
- Extract claim-card references from case study markdown and enforce linkage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple, Any
import re

__all__ = [
    "ClaimCard",
    "REQUIRED_FIELDS",
    "ALLOWED_VERIFICATION_STATUS",
    "ALLOWED_EVIDENCE_TYPES",
    "parse_claim_card_markdown",
    "validate_claim_card",
    "extract_claim_card_ids",
    "validate_case_study_text",
]


ALLOWED_VERIFICATION_STATUS = ("unverified", "partially", "verified")
ALLOWED_EVIDENCE_TYPES = (
    "experiment",
    "observational",
    "simulation",
    "meta-analysis",
    "review",
    "theory",
    "dataset",
    "benchmark",
    "anecdotal",
    "other",
)

REQUIRED_FIELDS = (
    "claim_text",
    "scope",
    "evidence_type",
    "citations",
    "verification_status",
    "abstention_triggers",
)


@dataclass(frozen=True)
class ClaimCard:
    claim_text: str
    scope: str
    evidence_type: str
    citations: List[str]
    verification_status: str
    abstention_triggers: List[str]
    claim_card_id: Optional[str] = None


_FIELD_ALIASES = {
    "claim text": "claim_text",
    "claim_text": "claim_text",
    "scope": "scope",
    "evidence type": "evidence_type",
    "evidence_type": "evidence_type",
    "citations/dois/urls": "citations",
    "citations": "citations",
    "dois": "citations",
    "urls": "citations",
    "verification status": "verification_status",
    "verification_status": "verification_status",
    "abstention triggers": "abstention_triggers",
    "abstention_triggers": "abstention_triggers",
    "claim card id": "claim_card_id",
    "claim_card_id": "claim_card_id",
}


def _norm_key(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def _split_list_value(v: str) -> List[str]:
    v = v.strip()
    if not v:
        return []
    parts = []
    for line in v.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^[-*]\s+(.*)$", line)
        if m:
            parts.append(m.group(1).strip())
        else:
            parts.extend([p.strip() for p in re.split(r"\s*,\s*", line) if p.strip()])
    return [p for p in parts if p]


def parse_claim_card_markdown(text: str) -> Dict[str, Any]:
    """Parse a claim card markdown document into a dict of known fields.

    Supports either:
    - 'Field: value' lines
    - Markdown headings '## Field' followed by content until next heading.
    """
    out: Dict[str, Any] = {}
    t = text.replace("\r\n", "\n").replace("\r", "\n")

    # Heading sections: ## Field Name
    heading_re = re.compile(r"^#{2,3}\s+(.+?)\s*$", re.M)
    headings = [(m.start(), m.end(), m.group(1)) for m in heading_re.finditer(t)]
    for i, (s, e, name) in enumerate(headings):
        key = _FIELD_ALIASES.get(_norm_key(name))
        if not key:
            continue
        body_start = e
        body_end = headings[i + 1][0] if i + 1 < len(headings) else len(t)
        body = t[body_start:body_end].strip("\n")
        if key in ("citations", "abstention_triggers"):
            out[key] = _split_list_value(body)
        else:
            out[key] = body.strip()

    # Fallback: Field: value
    for line in t.splitlines():
        m = re.match(r"^\s*([^:#]{2,80}?)[\s]*:\s*(.*?)\s*$", line)
        if not m:
            continue
        key = _FIELD_ALIASES.get(_norm_key(m.group(1)))
        if not key or key in out:
            continue
        val = m.group(2)
        if key in ("citations", "abstention_triggers"):
            out[key] = _split_list_value(val)
        else:
            out[key] = val.strip()

    return out


def validate_claim_card(card: Dict[str, Any] | ClaimCard) -> Tuple[bool, List[str]]:
    """Validate required fields, allowed values, and basic formatting."""
    if isinstance(card, ClaimCard):
        d = {
            "claim_text": card.claim_text,
            "scope": card.scope,
            "evidence_type": card.evidence_type,
            "citations": list(card.citations),
            "verification_status": card.verification_status,
            "abstention_triggers": list(card.abstention_triggers),
            "claim_card_id": card.claim_card_id,
        }
    else:
        d = dict(card)

    errors: List[str] = []
    for f in REQUIRED_FIELDS:
        v = d.get(f)
        if v is None or (isinstance(v, str) and not v.strip()) or (isinstance(v, list) and not v):
            errors.append(f"missing_or_empty:{f}")

    ev = str(d.get("evidence_type") or "").strip().lower()
    if ev and ev not in ALLOWED_EVIDENCE_TYPES:
        errors.append("invalid:evidence_type")

    vs = str(d.get("verification_status") or "").strip().lower()
    if vs and vs not in ALLOWED_VERIFICATION_STATUS:
        errors.append("invalid:verification_status")

    cits = d.get("citations")
    if isinstance(cits, list):
        for c in cits:
            if not isinstance(c, str) or not c.strip():
                errors.append("invalid:citations")
                break
    elif cits is not None:
        errors.append("invalid:citations")

    abst = d.get("abstention_triggers")
    if isinstance(abst, list):
        for a in abst:
            if not isinstance(a, str) or not a.strip():
                errors.append("invalid:abstention_triggers")
                break
    elif abst is not None:
        errors.append("invalid:abstention_triggers")

    return (len(errors) == 0), errors


_CC_ID_RE = re.compile(r"\bCC-[A-Za-z0-9][A-Za-z0-9_-]{2,63}\b")


def extract_claim_card_ids(text: str) -> List[str]:
    """Extract claim card IDs (e.g., CC-xyz123) from markdown/text."""
    return sorted(set(_CC_ID_RE.findall(text or "")))


def validate_case_study_text(case_text: str, *, claim_lines_regex: str = r"(?i)\bempirical\s*claim\b") -> Tuple[bool, List[str]]:
    """Enforce that each empirical-claim line references at least one claim card ID.

    Policy: Any line matching `claim_lines_regex` must include a CC-... identifier.
    """
    errors: List[str] = []
    if not case_text:
        return False, ["missing_or_empty:case_study_text"]

    line_re = re.compile(claim_lines_regex)
    for i, line in enumerate(case_text.splitlines(), start=1):
        if line_re.search(line):
            if not _CC_ID_RE.search(line):
                errors.append(f"empirical_claim_missing_claim_card_id:line_{i}")
    return (len(errors) == 0), errors
