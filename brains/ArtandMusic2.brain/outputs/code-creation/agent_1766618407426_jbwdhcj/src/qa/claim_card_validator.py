"""Claim card validator for QA gating.

Loads CLAIM_CARD YAML or Markdown with YAML frontmatter and validates:
- required inputs: verbatim_claim, source_context, provenance_anchor
- basic format constraints (non-empty strings, provenance anchor structure)
- status lifecycle transitions (for QA gate enforcement)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


FrontmatterDict = Dict[str, Any]


class ClaimCardError(ValueError):
    pass


_STATUS_ORDER = ["draft", "captured", "in_review", "verified", "disputed", "rejected", "archived"]
_ALLOWED_TRANSITIONS = {
    None: {"draft", "captured"},
    "draft": {"draft", "captured", "rejected"},
    "captured": {"captured", "in_review", "rejected"},
    "in_review": {"in_review", "verified", "disputed", "rejected"},
    "verified": {"verified", "disputed", "archived"},
    "disputed": {"disputed", "in_review", "rejected", "archived"},
    "rejected": {"rejected", "archived"},
    "archived": {"archived"},
}

_REQ_FIELDS = ("verbatim_claim", "source_context", "provenance_anchor")
_NONEMPTY_STR_FIELDS = ("verbatim_claim", "source_context")


def _parse_yaml(text: str) -> FrontmatterDict:
    if yaml is None:
        raise ClaimCardError("PyYAML is required to parse YAML claim cards.")
    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict):
        raise ClaimCardError("YAML content must be a mapping/object.")
    return data


def load_claim_card(path: Union[str, Path]) -> FrontmatterDict:
    p = Path(path)
    txt = p.read_text(encoding="utf-8")
    if p.suffix.lower() in {".yaml", ".yml"}:
        return _parse_yaml(txt)

    # Markdown: YAML frontmatter at start delimited by --- ... ---
    if txt.lstrip().startswith("---"):
        m = re.match(r"\A\s*---\s*\n(.*?)\n---\s*\n?", txt, flags=re.S)
        if not m:
            raise ClaimCardError("Invalid Markdown frontmatter; expected '---' block at top.")
        return _parse_yaml(m.group(1))

    # Markdown without frontmatter is not a valid claim card
    raise ClaimCardError("Markdown claim card must include YAML frontmatter at the top.")


def _is_nonempty_str(x: Any) -> bool:
    return isinstance(x, str) and bool(x.strip())


def _validate_provenance_anchor(anchor: Any) -> List[str]:
    errs: List[str] = []
    if isinstance(anchor, str):
        s = anchor.strip()
        if not s:
            return ["provenance_anchor must be a non-empty string or object."]
        # Require either URL, file path, or explicit fragment anchor marker
        if not (re.search(r"^https?://", s) or "#" in s or re.search(r"\.(pdf|md|txt|html|csv|json|yaml|yml)(#.+)?$", s, re.I)):
            errs.append("provenance_anchor string must look like a URL, file reference, or include a '#' fragment anchor.")
        return errs

    if isinstance(anchor, dict):
        t = anchor.get("type")
        v = anchor.get("value")
        if not _is_nonempty_str(t):
            errs.append("provenance_anchor.type is required and must be a non-empty string.")
        if not _is_nonempty_str(v):
            errs.append("provenance_anchor.value is required and must be a non-empty string.")
        loc = anchor.get("locator")
        if loc is not None and not isinstance(loc, (str, dict, list)):
            errs.append("provenance_anchor.locator must be a string, object, or list if provided.")
        return errs

    return ["provenance_anchor must be a string or mapping/object."]


def _validate_status_lifecycle(card: FrontmatterDict, previous_status: Optional[str]) -> List[str]:
    errs: List[str] = []
    status = card.get("status") or card.get("claim_status")
    if status is None:
        return ["status is required (e.g., draft/captured/in_review/verified/disputed/rejected/archived)."]
    if not _is_nonempty_str(status):
        return ["status must be a non-empty string."]
    status = status.strip()
    if status not in _STATUS_ORDER:
        errs.append(f"status must be one of: {', '.join(_STATUS_ORDER)}.")
        return errs

    prev = previous_status.strip() if isinstance(previous_status, str) else previous_status
    if prev is not None and prev not in _ALLOWED_TRANSITIONS:
        errs.append(f"previous_status '{prev}' is unknown.")
    allowed = _ALLOWED_TRANSITIONS.get(prev, set())
    if status not in allowed:
        errs.append(f"Invalid status transition: {prev!r} -> {status!r}. Allowed: {sorted(allowed)}")

    hist = card.get("status_history")
    if hist is not None:
        if not isinstance(hist, list) or not all(isinstance(x, (str, dict)) for x in hist):
            errs.append("status_history must be a list of status strings or objects.")
        else:
            seq: List[str] = []
            for item in hist:
                s = item.get("status") if isinstance(item, dict) else item
                if not _is_nonempty_str(s) or s.strip() not in _STATUS_ORDER:
                    errs.append("status_history contains an invalid status.")
                    break
                seq.append(s.strip())
            for a, b in zip(seq, seq[1:]):
                if b not in _ALLOWED_TRANSITIONS.get(a, set()):
                    errs.append(f"Invalid status_history transition: {a!r} -> {b!r}.")
                    break
            if seq and seq[-1] != status:
                errs.append("status_history last status must match status.")
    return errs


def validate_claim_card(card: FrontmatterDict, previous_status: Optional[str] = None) -> Tuple[bool, List[str]]:
    errs: List[str] = []
    if not isinstance(card, dict):
        return False, ["Claim card content must be a mapping/object."]

    for k in _REQ_FIELDS:
        if k not in card:
            errs.append(f"Missing required field: {k}")
    for k in _NONEMPTY_STR_FIELDS:
        if k in card and not _is_nonempty_str(card.get(k)):
            errs.append(f"{k} must be a non-empty string.")
    if "provenance_anchor" in card:
        errs.extend(_validate_provenance_anchor(card.get("provenance_anchor")))

    errs.extend(_validate_status_lifecycle(card, previous_status))
    return (len(errs) == 0), errs


@dataclass
class ValidationResult:
    ok: bool
    errors: List[str]
    card: Optional[FrontmatterDict] = None


class ClaimCardValidator:
    """Primary entrypoint for QA gate wiring."""

    def validate_path(self, path: Union[str, Path], previous_status: Optional[str] = None) -> ValidationResult:
        try:
            card = load_claim_card(path)
        except Exception as e:
            return ValidationResult(False, [str(e)], None)
        ok, errors = validate_claim_card(card, previous_status=previous_status)
        return ValidationResult(ok, errors, card)


def qa_gate_check(path: Union[str, Path], previous_status: Optional[str] = None) -> Tuple[bool, str]:
    """QA gate helper: returns (pass, message)."""
    res = ClaimCardValidator().validate_path(path, previous_status=previous_status)
    if res.ok:
        return True, "CLAIM_CARD validation passed."
    return False, "CLAIM_CARD validation failed: " + "; ".join(res.errors)
