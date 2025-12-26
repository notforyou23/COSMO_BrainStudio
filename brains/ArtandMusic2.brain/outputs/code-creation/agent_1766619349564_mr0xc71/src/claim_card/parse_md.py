"""Parse Markdown Claim Cards with YAML front matter into normalized JSON-ready dicts.

A Claim Card Markdown file is expected to start with YAML front matter delimited by
'---' lines. The remainder is treated as the human-readable body.

This module focuses on robust parsing + normalization for schema validation and
pilot logging (missing metadata, version ambiguity, correction history).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
from typing import Any, Dict, Optional, Tuple

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


@dataclass
class ParseResult:
    obj: Dict[str, Any]
    warnings: list[str]


class ClaimCardParseError(ValueError):
    pass


_FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _parse_front_matter(md_text: str) -> Tuple[Optional[dict], str]:
    m = _FRONT_MATTER_RE.match(md_text)
    if not m:
        return None, md_text
    yaml_text = m.group(1)
    body = md_text[m.end():]
    if yaml is None:
        raise ClaimCardParseError("PyYAML is required to parse YAML front matter.")
    data = yaml.safe_load(yaml_text) if yaml_text.strip() else {}
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ClaimCardParseError("YAML front matter must parse to a mapping/object.")
    return data, body


def _coerce_list(v: Any) -> list:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]


def _normalize_ids(obj: Dict[str, Any]) -> None:
    # Common aliases for id-like fields.
    if "claim_id" not in obj and "id" in obj:
        obj["claim_id"] = obj.pop("id")
    if "card_version" not in obj and "version" in obj:
        obj["card_version"] = obj.pop("version")
    if "schema_version" not in obj and "schema" in obj:
        obj["schema_version"] = obj.pop("schema")
    # Keep strings as strings.
    for k in ("claim_id", "card_version", "schema_version"):
        if k in obj and obj[k] is not None and not isinstance(obj[k], str):
            obj[k] = str(obj[k])


def _normalize_corrections(obj: Dict[str, Any], warnings: list[str]) -> None:
    # correction_history should be a list of objects; tolerate missing/alternate keys.
    if "correction_history" not in obj and "corrections" in obj:
        obj["correction_history"] = obj.pop("corrections")
    ch = obj.get("correction_history")
    if ch is None:
        return
    if not isinstance(ch, list):
        obj["correction_history"] = _coerce_list(ch)
        warnings.append("correction_history_coerced_to_list")
        ch = obj["correction_history"]
    fixed = []
    for i, entry in enumerate(ch):
        if entry is None:
            continue
        if isinstance(entry, str):
            fixed.append({"note": entry})
            warnings.append(f"correction_history_entry_{i}_coerced_from_string")
            continue
        if isinstance(entry, dict):
            fixed.append(entry)
            continue
        fixed.append({"note": str(entry)})
        warnings.append(f"correction_history_entry_{i}_coerced_to_note")
    obj["correction_history"] = fixed


def normalize_claim_card(obj: Dict[str, Any], body_md: str, *, source_path: Optional[str] = None,
                         raw_text: Optional[str] = None) -> ParseResult:
    warnings: list[str] = []
    if not isinstance(obj, dict):
        raise ClaimCardParseError("Claim Card front matter must be a mapping/object.")
    obj = dict(obj)  # shallow copy
    _normalize_ids(obj)
    _normalize_corrections(obj, warnings)

    # Move/attach body to a consistent key.
    if "body_markdown" not in obj:
        obj["body_markdown"] = body_md.lstrip("\n")
    elif not isinstance(obj.get("body_markdown"), str):
        obj["body_markdown"] = str(obj["body_markdown"])
        warnings.append("body_markdown_coerced_to_string")

    # Ensure verbatim claim presence from common aliases (do not fabricate content).
    if "verbatim_claim" not in obj:
        for alias in ("claim", "verbatim", "statement"):
            if alias in obj:
                obj["verbatim_claim"] = obj.pop(alias)
                warnings.append(f"verbatim_claim_aliased_from_{alias}")
                break

    # Minimal provenance normalization
    if "provenance" in obj and not isinstance(obj["provenance"], dict):
        obj["provenance"] = {"value": obj["provenance"]}
        warnings.append("provenance_wrapped")

    # Attach parse metadata for pilot logging.
    meta = obj.get("_parse_meta")
    if meta is None or not isinstance(meta, dict):
        meta = {}
    meta.setdefault("parsed_at", _utc_now_iso())
    if source_path:
        meta.setdefault("source_path", source_path)
    if raw_text is not None:
        meta.setdefault("raw_sha256", _sha256(raw_text))
        meta.setdefault("raw_bytes", len(raw_text.encode("utf-8")))
    obj["_parse_meta"] = meta

    return ParseResult(obj=obj, warnings=warnings)


def parse_claim_card_markdown(md_text: str, *, source_path: Optional[str] = None) -> ParseResult:
    fm, body = _parse_front_matter(md_text)
    if fm is None:
        # Return an object suitable for validation; schema will flag missing metadata.
        fm = {}
        warnings = ["missing_yaml_front_matter"]
        res = normalize_claim_card(fm, md_text, source_path=source_path, raw_text=md_text)
        res.warnings[:0] = warnings
        return res
    return normalize_claim_card(fm, body, source_path=source_path, raw_text=md_text)


def load_claim_card(path: str | Path) -> ParseResult:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    return parse_claim_card_markdown(text, source_path=str(p))


def to_json(obj: Dict[str, Any], *, indent: int = 2) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=indent)
