"""Metadata schema + helpers for PsyPrim primary-source records."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_ID = "https://psyprim.dev/schema/primary_source_record.schema.json"

PROVENANCE_FLAGS = [
    "scanned_pdf",
    "born_digital",
    "ocr",
    "transcribed",
    "translated",
    "verified_against_original",
    "secondary_citation",
    "uncertain_authorship",
    "uncertain_date",
    "redacted",
    "derived",
]

SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": SCHEMA_ID,
    "title": "PsyPrim PrimarySourceRecord",
    "type": "object",
    "additionalProperties": False,
    "required": ["record_id", "title", "record_type", "created_at", "repository_links"],
    "properties": {
        "record_id": {"type": "string", "minLength": 1},
        "title": {"type": "string", "minLength": 1},
        "record_type": {"type": "string", "enum": ["primary_source", "archive_item", "edition", "dataset", "image", "audio", "other"]},
        "created_at": {"type": "string", "format": "date-time"},
        "modified_at": {"type": "string", "format": "date-time"},
        "creators": {"type": "array", "items": {"type": "string", "minLength": 1}},
        "date_issued": {"type": "string", "minLength": 1},
        "language": {"type": "string", "minLength": 2},
        "abstract": {"type": "string"},
        "keywords": {"type": "array", "items": {"type": "string", "minLength": 1}},
        "notes": {"type": "string"},
        "provenance": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "flags": {"type": "array", "items": {"type": "string", "enum": PROVENANCE_FLAGS}, "uniqueItems": True},
                "statement": {"type": "string"},
                "checked_by": {"type": "string"},
                "checked_at": {"type": "string", "format": "date-time"},
            },
        },
        "repository_links": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["repo_id", "repo_name"],
                "properties": {
                    "repo_id": {"type": "string", "minLength": 1},
                    "repo_name": {"type": "string", "minLength": 1},
                    "repo_type": {"type": "string", "enum": ["archive", "library", "publisher", "database", "personal", "other"]},
                    "url": {"type": "string", "format": "uri"},
                    "persistent_id": {"type": "string"},
                    "access_date": {"type": "string", "format": "date"},
                    "citation_hint": {"type": "string"},
                },
            },
        },
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["cite_id", "full"],
                "properties": {
                    "cite_id": {"type": "string", "minLength": 1},
                    "style": {"type": "string"},
                    "full": {"type": "string", "minLength": 1},
                    "locator": {"type": "string"},
                    "doi": {"type": "string"},
                    "url": {"type": "string", "format": "uri"},
                    "repository_ref": {"type": "string"},
                },
            },
        },
        "variants": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["variant_no", "label", "created_at"],
                "properties": {
                    "variant_no": {"type": "integer", "minimum": 1},
                    "label": {"type": "string", "minLength": 1},
                    "based_on": {"type": "integer", "minimum": 1},
                    "changes": {"type": "string"},
                    "created_at": {"type": "string", "format": "date-time"},
                },
            },
        },
    },
}

def schema() -> Dict[str, Any]:
    return deepcopy(SCHEMA)

def _iso_dt(x: Any) -> str:
    if isinstance(x, datetime):
        return x.replace(microsecond=0).isoformat()
    return str(x)

def _iso_d(x: Any) -> str:
    if isinstance(x, date):
        return x.isoformat()
    return str(x)

def new_record(record_id: str, title: str, record_type: str = "primary_source") -> Dict[str, Any]:
    return {
        "record_id": record_id,
        "title": title,
        "record_type": record_type,
        "created_at": _iso_dt(datetime.utcnow()),
        "repository_links": [],
    }

def add_repository_link(rec: Dict[str, Any], repo_id: str, repo_name: str, **kwargs: Any) -> None:
    rec.setdefault("repository_links", []).append({"repo_id": repo_id, "repo_name": repo_name, **kwargs})

def link_citation_to_repo(citation: Dict[str, Any], repo_id: str) -> Dict[str, Any]:
    c = dict(citation)
    c["repository_ref"] = repo_id
    return c

def next_variant_no(rec: Dict[str, Any]) -> int:
    nums = [v.get("variant_no") for v in rec.get("variants", []) if isinstance(v, dict)]
    nums = [n for n in nums if isinstance(n, int) and n >= 1]
    return (max(nums) + 1) if nums else 1

def add_variant(rec: Dict[str, Any], label: str, based_on: Optional[int] = None, changes: str = "") -> Dict[str, Any]:
    v = {"variant_no": next_variant_no(rec), "label": label, "created_at": _iso_dt(datetime.utcnow())}
    if based_on is not None:
        v["based_on"] = based_on
    if changes:
        v["changes"] = changes
    rec.setdefault("variants", []).append(v)
    return v

def validate_record(rec: Dict[str, Any], raise_on_error: bool = True) -> List[str]:
    errors: List[str] = []
    try:
        import jsonschema  # type: ignore
        try:
            from jsonschema import Draft202012Validator  # type: ignore
            v = Draft202012Validator(SCHEMA)
            errors = [f"{'/'.join(map(str,e.path)) or '<root>'}: {e.message}" for e in sorted(v.iter_errors(rec), key=lambda e: list(e.path))]
        except Exception:
            jsonschema.validate(instance=rec, schema=SCHEMA)  # type: ignore
            errors = []
    except Exception:
        for k in SCHEMA.get("required", []):
            if k not in rec:
                errors.append(f"<root>: missing required property '{k}'")
        if "repository_links" in rec and not isinstance(rec["repository_links"], list):
            errors.append("repository_links: must be array")
    if raise_on_error and errors:
        raise ValueError("Schema validation failed: " + "; ".join(errors))
    return errors

def minimal_checklist(rec: Dict[str, Any]) -> List[Tuple[str, bool, str]]:
    prov = rec.get("provenance", {}) if isinstance(rec.get("provenance"), dict) else {}
    flags = set(prov.get("flags") or [])
    repo_ok = bool(rec.get("repository_links"))
    cite_ok = bool(rec.get("citations"))
    return [
        ("Has repository link(s)", repo_ok, "Add at least one repository_links entry with repo_name + stable URL/ID."),
        ("Has at least one full citation", cite_ok, "Add citations.full with a complete reference and locator if applicable."),
        ("Provenance flags recorded", bool(flags), "Add provenance.flags for scan/OCR/transcription/verification, etc."),
    ]
