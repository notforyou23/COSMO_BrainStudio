"""Hard-fail validators for claim-card intake.

Goal: reject claim cards missing required claim text or dataset anchor and emit
clear error messages for primary-source verification workflows.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Union
@dataclass(frozen=True)
class IntakeValidationError(ValueError):
    """Raised when intake validation fails (hard-fail)."""

    errors: Sequence[str]

    def __str__(self) -> str:
        if not self.errors:
            return "Intake validation failed."
        if len(self.errors) == 1:
            return self.errors[0]
        return "Intake validation failed:\n- " + "\n- ".join(self.errors)
def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def _as_location(path: Optional[Union[str, Sequence[Union[str, int]]]]) -> str:
    if path is None:
        return ""
    if isinstance(path, str):
        return path
    parts: List[str] = []
    for p in path:
        parts.append(str(p))
    return "/".join(parts)
def _req_str(obj: Dict[str, Any], key: str, *, loc: str = "") -> Optional[str]:
    if key not in obj:
        return None
    val = obj.get(key)
    if isinstance(val, str):
        return val
    if val is None:
        return ""
    raise IntakeValidationError([f"{loc + ': ' if loc else ''}{key} must be a string."])


def _validate_dataset_anchor(value: Any, *, loc: str = "") -> List[str]:
    errs: List[str] = []
    if value is None:
        errs.append(f"{loc + ': ' if loc else ''}dataset_anchor is required (missing).")
        return errs
    if isinstance(value, str):
        if value.strip() == "":
            errs.append(f"{loc + ': ' if loc else ''}dataset_anchor is required (blank).")
        return errs
    if isinstance(value, dict):
        # Accept common anchor shapes; require at least one meaningful pointer.
        candidate_keys = ("dataset_id", "dataset", "source", "url", "uri", "path", "table", "query", "sha256", "fingerprint")
        if not any((k in value and not _is_blank(value.get(k))) for k in candidate_keys):
            errs.append(
                f"{loc + ': ' if loc else ''}dataset_anchor dict must include at least one non-blank key among: "
                + ", ".join(candidate_keys)
                + "."
            )
        return errs
    errs.append(f"{loc + ': ' if loc else ''}dataset_anchor must be a string or object.")
    return errs
def validate_claim_card(card: Dict[str, Any], *, path: Optional[Union[str, Sequence[Union[str, int]]]] = None) -> None:
    """Hard-fail validation for a single claim card.

    Required fields (hard fail):
      - claim_text: non-blank string describing the claim to verify
      - dataset_anchor: non-blank string or object anchoring the dataset/source pointer
    """
    loc = _as_location(path)
    errors: List[str] = []

    if not isinstance(card, dict):
        raise IntakeValidationError([f"{loc + ': ' if loc else ''}claim card must be an object/dict."])

    claim_text = _req_str(card, "claim_text", loc=loc)
    if claim_text is None:
        errors.append(f"{loc + ': ' if loc else ''}claim_text is required (missing).")
    elif claim_text.strip() == "":
        errors.append(f"{loc + ': ' if loc else ''}claim_text is required (blank).")

    errors.extend(_validate_dataset_anchor(card.get("dataset_anchor", None), loc=loc))

    if errors:
        raise IntakeValidationError(errors)


def validate_claim_cards(cards: Iterable[Dict[str, Any]], *, path: str = "claim_cards") -> None:
    """Hard-fail validation for an iterable of claim cards."""
    all_errors: List[str] = []
    for i, card in enumerate(cards):
        try:
            validate_claim_card(card, path=(path, i))
        except IntakeValidationError as e:
            all_errors.extend(list(e.errors))
    if all_errors:
        raise IntakeValidationError(all_errors)
