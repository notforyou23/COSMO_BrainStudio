"""QA report schema + lightweight validation helpers.

This module defines a stable, machine-validated structure for QA_REPORT.json.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

REPORT_VERSION = "1.0"
ALLOWED_STATUSES = ("PASS", "FAIL", "WARN", "SKIP")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


QA_REPORT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["version", "generated_at", "target", "summary", "checks"],
    "properties": {
        "version": {"type": "string"},
        "generated_at": {"type": "string"},
        "target": {
            "type": "object",
            "required": ["report_path"],
            "properties": {
                "report_path": {"type": "string"},
                "artifacts_root": {"type": ["string", "null"]},
            },
        },
        "summary": {
            "type": "object",
            "required": ["status", "counts"],
            "properties": {
                "status": {"type": "string", "enum": list(ALLOWED_STATUSES)},
                "counts": {
                    "type": "object",
                    "required": ["PASS", "FAIL", "WARN", "SKIP"],
                    "properties": {k: {"type": "integer"} for k in ALLOWED_STATUSES},
                },
            },
        },
        "checks": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "name", "status", "message", "remediation"],
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "status": {"type": "string", "enum": list(ALLOWED_STATUSES)},
                    "message": {"type": "string"},
                    "errors": {"type": "array", "items": {"type": "string"}},
                    "remediation": {"type": "array", "items": {"type": "string"}},
                    "pointers": {
                        "type": "array",
                        "items": {"type": "object", "required": ["kind", "ref"], "properties": {"kind": {"type": "string"}, "ref": {"type": "string"}}},
                    },
                    "meta": {"type": "object"},
                },
            },
        },
        "meta": {"type": "object"},
    },
}


@dataclass(frozen=True)
class ValidationError:
    path: str
    message: str


def _is_type(val: Any, t: Any) -> bool:
    if t == "object":
        return isinstance(val, dict)
    if t == "array":
        return isinstance(val, list)
    if t == "string":
        return isinstance(val, str)
    if t == "integer":
        return isinstance(val, int) and not isinstance(val, bool)
    if t == "null":
        return val is None
    return True


def _validate(schema: Dict[str, Any], value: Any, path: str, out: List[ValidationError]) -> None:
    if "type" in schema:
        st = schema["type"]
        ok = any(_is_type(value, t) for t in st) if isinstance(st, list) else _is_type(value, st)
        if not ok:
            out.append(ValidationError(path, f"expected {st}, got {type(value).__name__}"))
            return
    if "enum" in schema and value not in schema["enum"]:
        out.append(ValidationError(path, f"must be one of {schema['enum']!r}"))
        return
    if isinstance(value, dict):
        req = schema.get("required", [])
        for k in req:
            if k not in value:
                out.append(ValidationError(f"{path}.{k}" if path else k, "missing required field"))
        props = schema.get("properties", {})
        for k, v in value.items():
            if k in props:
                _validate(props[k], v, f"{path}.{k}" if path else k, out)
    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            _validate(schema["items"], item, f"{path}[{i}]", out)


def validate_report(report: Dict[str, Any]) -> Tuple[bool, List[ValidationError]]:
    errs: List[ValidationError] = []
    _validate(QA_REPORT_SCHEMA, report, "", errs)
    return (len(errs) == 0), errs


def assert_valid_report(report: Dict[str, Any]) -> None:
    ok, errs = validate_report(report)
    if ok:
        return
    msg = "; ".join(f"{e.path}: {e.message}" for e in errs[:50])
    if len(errs) > 50:
        msg += f"; (+{len(errs)-50} more)"
    raise ValueError(f"QA report failed schema validation: {msg}")


def normalize_report(report: Dict[str, Any]) -> Dict[str, Any]:
    """Return a sanitized copy with required top-level keys present when possible."""
    r = dict(report or {})
    r.setdefault("version", REPORT_VERSION)
    r.setdefault("generated_at", now_iso())
    r.setdefault("meta", {})
    r.setdefault("checks", [])
    r.setdefault("target", {"report_path": ""})
    r.setdefault("summary", {"status": "SKIP", "counts": {k: 0 for k in ALLOWED_STATUSES}})
    return r
