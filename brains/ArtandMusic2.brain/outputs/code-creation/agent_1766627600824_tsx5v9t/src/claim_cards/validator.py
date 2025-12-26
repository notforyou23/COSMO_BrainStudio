from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import re

try:
    import jsonschema  # type: ignore
except Exception:  # pragma: no cover
    jsonschema = None

_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[T\s]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})?)?$")

def _get(d: Any, path: str) -> Any:
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur

def _first(d: Any, paths: List[str]) -> Any:
    for p in paths:
        v = _get(d, p)
        if v is not None:
            return v
    return None

def _is_nonempty_str(v: Any) -> bool:
    return isinstance(v, str) and v.strip() != ""

def _is_url(v: Any) -> bool:
    return _is_nonempty_str(v) and bool(_URL_RE.match(v.strip()))

def _is_iso_date(v: Any) -> bool:
    return _is_nonempty_str(v) and bool(_ISO_DATE_RE.match(v.strip()))

class AbstentionError(ValueError):
    """Raised when required intake checklist fields are missing or unsupported."""

@dataclass
class ValidationResult:
    status: str  # 'pass' | 'fail' | 'abstain'
    errors: List[str]
    abstain_reason: Optional[str] = None

def load_schema(schema_path: Optional[str | Path] = None) -> Optional[Dict[str, Any]]:
    if schema_path is None:
        schema_path = Path(__file__).resolve().parents[2] / "config" / "claim_card_schema.json"
    p = Path(schema_path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))

def validate_against_schema(obj: Dict[str, Any], schema: Optional[Dict[str, Any]]) -> List[str]:
    if not schema or jsonschema is None:
        return []
    v = jsonschema.Draft202012Validator(schema)
    errs = []
    for e in sorted(v.iter_errors(obj), key=lambda x: x.path):
        loc = ".".join(str(p) for p in e.path) if e.path else "$"
        errs.append(f"schema:{loc}:{e.message}")
    return errs

def _required_fields_check(obj: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """Returns (abstain_errors, hard_fail_errors). Missing required => abstain."""
    abstain: List[str] = []
    fail: List[str] = []

    claim_text = _first(obj, [
        "claim.text_verbatim",
        "claim.verbatim_text",
        "claim_text_verbatim",
        "verbatim_claim_text",
        "claim.text",
        "claim_text",
    ])
    verbatim_flag = _first(obj, [
        "claim.is_verbatim",
        "claim.verbatim",
        "is_verbatim",
        "verbatim",
    ])

    if not _is_nonempty_str(claim_text):
        abstain.append("missing_required:verbatim_claim_text")
    else:
        # Require explicit support for verbatim capture: either dedicated field name or flag true.
        used_dedicated = _is_nonempty_str(_first(obj, ["claim.text_verbatim", "claim.verbatim_text", "claim_text_verbatim", "verbatim_claim_text"]))
        if not used_dedicated and verbatim_flag is not True:
            abstain.append("unsupported:claim_text_not_marked_verbatim (provide claim.text_verbatim or is_verbatim=true)")

    speaker = _first(obj, ["context.speaker", "claim.context.speaker", "speaker"])
    date = _first(obj, ["context.date", "claim.context.date", "date"])
    link = _first(obj, ["context.link", "claim.context.link", "source.link", "source_url", "url", "link"])

    if not _is_nonempty_str(speaker):
        abstain.append("missing_required:context.speaker")
    if not _is_nonempty_str(date):
        abstain.append("missing_required:context.date")
    elif not _is_iso_date(date):
        fail.append("invalid_format:context.date (expected ISO date like YYYY-MM-DD or ISO datetime)")
    if not _is_nonempty_str(link):
        abstain.append("missing_required:context.link")
    elif not _is_url(link):
        fail.append("invalid_format:context.link (expected http(s) URL)")

    anchor = _first(obj, [
        "provenance.anchor",
        "claim.provenance.anchor",
        "provenance_anchor",
        "anchor",
        "provenance.quote_anchor",
        "claim.provenance.quote_anchor",
    ])
    if not _is_nonempty_str(anchor):
        abstain.append("missing_required:provenance.anchor")

    # Basic coherence: if anchor exists, require it to be findable/locatable (heuristic)
    if _is_nonempty_str(anchor):
        a = str(anchor).strip()
        if len(a) < 3:
            fail.append("invalid:provenance.anchor_too_short")
    return abstain, fail

def validate_claim_card(obj: Dict[str, Any], schema: Optional[Dict[str, Any]] = None, schema_path: Optional[str | Path] = None) -> ValidationResult:
    """Validates claim card data; abstains when required intake checklist fields are missing or unsupported."""
    errors: List[str] = []
    if not isinstance(obj, dict):
        return ValidationResult(status="abstain", errors=["missing_required:root_object"], abstain_reason="Root must be a JSON object/dict.")

    schema = schema if schema is not None else load_schema(schema_path)
    errors.extend(validate_against_schema(obj, schema))

    abstain_errors, fail_errors = _required_fields_check(obj)
    errors.extend(fail_errors)

    if abstain_errors:
        errors = abstain_errors + errors
        return ValidationResult(status="abstain", errors=errors, abstain_reason="Required intake checklist fields are missing or unsupported (must include verbatim claim text, context, and provenance anchor).")

    if errors:
        return ValidationResult(status="fail", errors=errors, abstain_reason=None)
    return ValidationResult(status="pass", errors=[], abstain_reason=None)

def assert_valid_or_raise(obj: Dict[str, Any], **kwargs: Any) -> None:
    res = validate_claim_card(obj, **kwargs)
    if res.status == "pass":
        return
    msg = "; ".join(res.errors) if res.errors else (res.abstain_reason or "validation_failed")
    if res.status == "abstain":
        raise AbstentionError(msg)
    raise ValueError(msg)
