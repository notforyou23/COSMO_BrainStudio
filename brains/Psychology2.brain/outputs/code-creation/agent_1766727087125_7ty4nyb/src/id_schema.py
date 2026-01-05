"""Canonical ID schema shared across extraction CSV, taxonomy JSONL, and prereg metadata.

IDs are expected to be ASCII, uppercase, hyphen-delimited, and normalized by:
- strip whitespace
- replace spaces/underscores with hyphens
- collapse repeated hyphens
- uppercase

Examples (valid after normalization):
- study_id:   STU-2025-0A7
- effect_id:  EFF-STU-2025-0A7-0001
- taxon_id:   TAX-NUDGE-DEFAULT
- prereg_id:  PREREG-OSF-1A2B3C4D
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Dict, Iterable, Mapping, Optional, Pattern, Tuple
# ---- Normalization ----

_ASCII_RE = re.compile(r"^[\x20-\x7E]+$")
_SEP_RE = re.compile(r"[\s_]+")
_DASH_RE = re.compile(r"-+")


def normalize_id(raw: object) -> str:
    """Normalize an ID-like value to canonical form; returns '' for None/empty."""
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    s = _SEP_RE.sub("-", s)
    s = _DASH_RE.sub("-", s)
    return s.upper()


def is_ascii_printable(s: str) -> bool:
    return bool(s) and bool(_ASCII_RE.match(s))
# ---- Canonical patterns ----

# Study IDs are stable anchors used across extraction/prereg and referenced by effect_id.
STUDY_ID_RE: Pattern[str] = re.compile(r"^STU-(?P<year>[0-9]{4})-(?P<code>[A-Z0-9]{3})$")

# Effect IDs are extraction-row identifiers that embed the study_id and a 4-digit within-study index.
EFFECT_ID_RE: Pattern[str] = re.compile(
    r"^EFF-(?P<study>STU-[0-9]{4}-[A-Z0-9]{3})-(?P<idx>[0-9]{4})$"
)

# Taxonomy node IDs (used in taxonomy JSONL) are namespaced and readable.
TAXON_ID_RE: Pattern[str] = re.compile(r"^TAX-[A-Z0-9]+(?:-[A-Z0-9]+){1,5}$")

# Preregistration IDs (e.g., OSF, AsPredicted) are namespaced by registry.
PREREG_ID_RE: Pattern[str] = re.compile(r"^PREREG-(?P<registry>[A-Z0-9]{2,12})-(?P<token>[A-Z0-9]{8,16})$")

# Some prereg sources also provide a registration URL; accept canonical-ish HTTP(S).
URL_RE: Pattern[str] = re.compile(r"^https?://\S+$", re.IGNORECASE)


PATTERNS: Dict[str, Pattern[str]] = {
    "study_id": STUDY_ID_RE,
    "effect_id": EFFECT_ID_RE,
    "taxon_id": TAXON_ID_RE,
    "prereg_id": PREREG_ID_RE,
    "url": URL_RE,
}
# ---- Uniqueness & referential rules ----

# These are generic constraints consumed by loaders/checkers.
# - `unique_within`: fields that must be unique within their own source.
# - `references`: pairs (field, target_field) indicating referential integrity.

UNIQUE_WITHIN: Dict[str, Tuple[str, ...]] = {
    "extraction": ("effect_id",),
    "taxonomy": ("taxon_id",),
    "prereg": ("prereg_id",),
}

# Cross-source referential expectations.
REFERENCES: Dict[str, Tuple[Tuple[str, str], ...]] = {
    # extraction.study_id should exist in prereg.study_id when prereg is provided
    "extraction->prereg": (("study_id", "study_id"),),
    # extraction.taxon_id should exist in taxonomy.taxon_id
    "extraction->taxonomy": (("taxon_id", "taxon_id"),),
}

# Optional co-constraints derived from embedded IDs.
# effect_id embeds study_id; this validates internal consistency.
DERIVED_CONSTRAINTS: Tuple[str, ...] = (
    "effect_id embeds study_id: EFFECT_ID_RE.group('study') == study_id",
,)
@dataclass(frozen=True)
class IDSchema:
    patterns: Mapping[str, Pattern[str]]
    unique_within: Mapping[str, Tuple[str, ...]]
    references: Mapping[str, Tuple[Tuple[str, str], ...]]

    def normalize(self, field: str, value: object) -> str:
        if field == "url":
            return str(value).strip() if value is not None else ""
        return normalize_id(value)

    def match(self, field: str, value: object) -> Optional[re.Match[str]]:
        s = self.normalize(field, value)
        if not s:
            return None
        pat = self.patterns.get(field)
        if pat is None:
            raise KeyError(f"Unknown schema field: {field}")
        return pat.match(s)

    def conforms(self, field: str, value: object) -> bool:
        s = self.normalize(field, value)
        if not s:
            return False
        if field != "url" and not is_ascii_printable(s):
            return False
        return self.match(field, s) is not None

    def explain(self, field: str) -> str:
        pat = self.patterns.get(field)
        if pat is None:
            raise KeyError(f"Unknown schema field: {field}")
        return pat.pattern
SCHEMA = IDSchema(patterns=PATTERNS, unique_within=UNIQUE_WITHIN, references=REFERENCES)


def extract_study_id_from_effect_id(effect_id: object) -> str:
    """Return embedded study_id from effect_id, else '' if nonconforming."""
    m = SCHEMA.match("effect_id", effect_id)
    return m.group("study") if m else ""


def validate_effect_embeds_study(effect_id: object, study_id: object) -> bool:
    """True iff effect_id and study_id both conform and are internally consistent."""
    eff = SCHEMA.normalize("effect_id", effect_id)
    stu = SCHEMA.normalize("study_id", study_id)
    if not (SCHEMA.conforms("effect_id", eff) and SCHEMA.conforms("study_id", stu)):
        return False
    return extract_study_id_from_effect_id(eff) == stu
