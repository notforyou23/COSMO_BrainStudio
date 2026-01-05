"""id_convention.py

Canonical ID convention shared by CSV and JSONL inputs.

IDs:
- study_id: S + 4-8 digits (e.g., S0001, S12345678)
- effect_id: {study_id}-E + 3-6 digits (e.g., S0001-E001, S12345678-E000123)

This module provides validators and parsers so both loaders enforce identical rules.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Tuple

STUDY_ID_COL = "study_id"
EFFECT_ID_COL = "effect_id"

# Example: S0001 .. S12345678
STUDY_ID_RE = re.compile(r"^S\d{4,8}$")

# Example: S0001-E001 .. S12345678-E000123
EFFECT_ID_RE = re.compile(r"^(S\d{4,8})-E(\d{3,6})$")

ID_DOC_EXAMPLES = {
    "study_id": ["S0001", "S12345678"],
    "effect_id": ["S0001-E001", "S12345678-E000123"],
}
@dataclass(frozen=True, slots=True)
class IdPair:
    study_id: str
    effect_id: str

    def __post_init__(self) -> None:
        # Keep this strict: an IdPair is only valid if both IDs are valid and consistent.
        validate_study_id(self.study_id)
        validate_effect_id(self.effect_id, expected_study_id=self.study_id)
def is_valid_study_id(study_id: object) -> bool:
    return isinstance(study_id, str) and STUDY_ID_RE.fullmatch(study_id) is not None


def is_valid_effect_id(effect_id: object) -> bool:
    return isinstance(effect_id, str) and EFFECT_ID_RE.fullmatch(effect_id) is not None


def validate_study_id(study_id: object, *, where: str = "") -> str:
    if not is_valid_study_id(study_id):
        loc = f" at {where}" if where else ""
        raise ValueError(
            f"Invalid study_id{loc}: {study_id!r}. Expected format "
            f"{STUDY_ID_RE.pattern} (e.g., {', '.join(ID_DOC_EXAMPLES['study_id'])})."
        )
    return str(study_id)
def split_effect_id(effect_id: object, *, where: str = "") -> Tuple[str, int]:
    if not isinstance(effect_id, str):
        loc = f" at {where}" if where else ""
        raise ValueError(f"Invalid effect_id{loc}: {effect_id!r}. Expected a string.")
    m = EFFECT_ID_RE.fullmatch(effect_id)
    if not m:
        loc = f" at {where}" if where else ""
        raise ValueError(
            f"Invalid effect_id{loc}: {effect_id!r}. Expected format "
            f"{EFFECT_ID_RE.pattern} (e.g., {', '.join(ID_DOC_EXAMPLES['effect_id'])})."
        )
    study_id = m.group(1)
    effect_num = int(m.group(2))
    return study_id, effect_num


def validate_effect_id(
    effect_id: object, *, expected_study_id: Optional[str] = None, where: str = ""
) -> str:
    parsed_study_id, _ = split_effect_id(effect_id, where=where)
    if expected_study_id is not None:
        validate_study_id(expected_study_id, where=where or "expected_study_id")
        if parsed_study_id != expected_study_id:
            loc = f" at {where}" if where else ""
            raise ValueError(
                f"effect_id study prefix mismatch{loc}: effect_id={effect_id!r} "
                f"implies study_id={parsed_study_id!r}, but record study_id={expected_study_id!r}."
            )
    return str(effect_id)


def canonicalize_pair(study_id: object, effect_id: object, *, where: str = "") -> IdPair:
    sid = validate_study_id(study_id, where=where or STUDY_ID_COL)
    eid = validate_effect_id(effect_id, expected_study_id=sid, where=where or EFFECT_ID_COL)
    return IdPair(study_id=sid, effect_id=eid)
