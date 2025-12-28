"""Canonical StudyID/EffectID convention and helpers.

Canonical formats:
- StudyID:  STUDY-0001
- EffectID: STUDY-0001:E001

Normalization accepts common variants (case-insensitive separators):
- StudyID:  study0001, Study_0001, STUDY-0001
- EffectID: study-0001:e1, STUDY0001_E001, study_0001-e001
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Tuple

STUDY_PREFIX = "STUDY"
STUDY_CANONICAL_RE = r"^STUDY-(?P<num>\d{4})$"
EFFECT_CANONICAL_RE = r"^(?P<study>STUDY-\d{4}):E(?P<eff>\d{3})$"

_STUDY_CANONICAL_PAT = re.compile(STUDY_CANONICAL_RE)
_EFFECT_CANONICAL_PAT = re.compile(EFFECT_CANONICAL_RE)

# Acceptable loose inputs (case-insensitive, flexible separators)
_STUDY_LOOSE_PAT = re.compile(r"^(?i:study)\s*[-_ ]?\s*(?P<num>\d{1,6})\s*$")
_EFFECT_LOOSE_PAT = re.compile(
    r"^\s*(?P<study>(?i:study)\s*[-_ ]?\s*\d{1,6})\s*[:._\- ]\s*(?P<e>(?i:e)\s*\d{1,6})\s*$"
)

class IDValidationError(ValueError):
    """Raised when an ID cannot be normalized/validated."""


@dataclass(frozen=True)
class ParsedEffectID:
    study_id: str
    effect_num: int

    @property
    def effect_id(self) -> str:
        return make_effect_id(self.study_id, self.effect_num)
def _strip(x: object) -> str:
    return "" if x is None else str(x).strip()


def is_valid_study_id(study_id: object) -> bool:
    return _STUDY_CANONICAL_PAT.match(_strip(study_id).upper()) is not None


def is_valid_effect_id(effect_id: object) -> bool:
    return _EFFECT_CANONICAL_PAT.match(_strip(effect_id).upper()) is not None


def normalize_study_id(study_id: object, *, strict: bool = False) -> str:
    """Normalize to canonical StudyID (STUDY-0001)."""
    raw = _strip(study_id)
    if not raw:
        raise IDValidationError("Missing StudyID")
    up = raw.upper()

    m = _STUDY_CANONICAL_PAT.match(up)
    if m:
        return f"{STUDY_PREFIX}-{int(m.group('num')):04d}"

    m = _STUDY_LOOSE_PAT.match(raw)
    if not m:
        raise IDValidationError(f"Invalid StudyID format: {raw!r}")
    num = int(m.group("num"))
    if strict and not (0 <= num <= 9999):
        raise IDValidationError(f"StudyID number out of canonical range (0000-9999): {raw!r}")
    return f"{STUDY_PREFIX}-{num:04d}"


def make_effect_id(study_id: object, effect_num: int) -> str:
    s = normalize_study_id(study_id)
    if effect_num is None:
        raise IDValidationError("Missing effect number")
    n = int(effect_num)
    if n < 0:
        raise IDValidationError(f"Effect number must be non-negative, got {effect_num!r}")
    return f"{s}:E{n:03d}"
def parse_effect_id(effect_id: object, *, strict: bool = False) -> ParsedEffectID:
    """Parse/normalize EffectID, returning canonical components."""
    raw = _strip(effect_id)
    if not raw:
        raise IDValidationError("Missing EffectID")
    up = raw.upper()

    m = _EFFECT_CANONICAL_PAT.match(up)
    if m:
        study = normalize_study_id(m.group("study"), strict=strict)
        eff = int(m.group("eff"))
        return ParsedEffectID(study_id=study, effect_num=eff)

    m = _EFFECT_LOOSE_PAT.match(raw)
    if not m:
        raise IDValidationError(f"Invalid EffectID format: {raw!r}")

    study = normalize_study_id(m.group("study"), strict=strict)
    e_raw = _strip(m.group("e"))
    e_m = re.match(r"^(?i:e)\s*(?P<num>\d{1,6})\s*$", e_raw)
    if not e_m:
        raise IDValidationError(f"Invalid effect component in EffectID: {raw!r}")
    eff = int(e_m.group("num"))
    if strict and not (0 <= eff <= 999):
        raise IDValidationError(f"Effect number out of canonical range (000-999): {raw!r}")
    return ParsedEffectID(study_id=study, effect_num=eff)


def normalize_effect_id(effect_id: object, *, strict: bool = False) -> str:
    p = parse_effect_id(effect_id, strict=strict)
    return make_effect_id(p.study_id, p.effect_num)


def split_effect_id(effect_id: object, *, strict: bool = False) -> Tuple[str, int]:
    p = parse_effect_id(effect_id, strict=strict)
    return p.study_id, p.effect_num
def ids_equal(a: object, b: object, *, kind: str) -> bool:
    """Compare IDs after normalization (kind: 'study' or 'effect')."""
    k = (kind or "").strip().lower()
    if k == "study":
        return normalize_study_id(a) == normalize_study_id(b)
    if k == "effect":
        return normalize_effect_id(a) == normalize_effect_id(b)
    raise ValueError("kind must be 'study' or 'effect'")


def compare_study_ids(a: object, b: object) -> bool:
    return ids_equal(a, b, kind="study")


def compare_effect_ids(a: object, b: object) -> bool:
    return ids_equal(a, b, kind="effect")


def coerce_ids(study_id: object = None, effect_id: object = None, *, strict: bool = False) -> Tuple[Optional[str], Optional[str]]:
    """Best-effort coercion: normalize provided IDs; if only EffectID is given, also returns StudyID."""
    s_norm: Optional[str] = None
    e_norm: Optional[str] = None

    if study_id is not None and _strip(study_id):
        s_norm = normalize_study_id(study_id, strict=strict)

    if effect_id is not None and _strip(effect_id):
        p = parse_effect_id(effect_id, strict=strict)
        e_norm = make_effect_id(p.study_id, p.effect_num)
        s_norm = s_norm or p.study_id

    return s_norm, e_norm
