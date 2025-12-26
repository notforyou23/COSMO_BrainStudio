"""Utilities to load and validate case-study metadata JSON against METADATA_SCHEMA.json.

Designed for CLI use: raise ValueError with clear, actionable messages.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import json


DEFAULT_SCHEMA_RELATIVE_PATH = Path("schemas") / "METADATA_SCHEMA.json"


def _project_root() -> Path:
    # src/utils/schema_validate.py -> project root is parents[2]
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise ValueError(f"File not found: {path}") from e
    except json.JSONDecodeError as e:
        loc = f"line {e.lineno}, column {e.colno}"
        raise ValueError(f"Invalid JSON in {path} ({loc}): {e.msg}") from e


def load_schema(schema_path: Optional[Path] = None) -> Dict[str, Any]:
    path = schema_path or (_project_root() / DEFAULT_SCHEMA_RELATIVE_PATH)
    obj = load_json(path)
    if not isinstance(obj, dict):
        raise ValueError(f"Schema must be a JSON object: {path}")
    return obj


@dataclass(frozen=True)
class ValidationIssue:
    instance_path: str
    schema_path: str
    message: str


def _to_json_pointer(parts: Sequence[Any]) -> str:
    def esc(p: Any) -> str:
        s = str(p)
        return s.replace("~", "~0").replace("/", "~1")
    return "" if not parts else "/" + "/".join(esc(p) for p in parts)


def _format_jsonschema_error(err: Any) -> ValidationIssue:
    inst = _to_json_pointer(getattr(err, "absolute_path", []) or getattr(err, "path", []))
    sch = _to_json_pointer(getattr(err, "absolute_schema_path", []) or getattr(err, "schema_path", []))
    msg = getattr(err, "message", "Validation error")
    v = getattr(err, "validator", None)

    if v == "required":
        missing = None
        try:
            missing = err.message.split("'")[1]
        except Exception:
            missing = None
        if missing:
            msg = f"Missing required property '{missing}'."
    elif v == "additionalProperties":
        extras = None
        try:
            # Message like: "Additional properties are not allowed ('x', 'y' were unexpected)"
            if "(" in err.message and "unexpected" in err.message:
                extras = err.message.split("(", 1)[1].split(")", 1)[0]
        except Exception:
            extras = None
        if extras:
            msg = f"Unexpected properties not allowed here: {extras}."
    elif v == "type":
        expected = getattr(err, "schema", None)
        if isinstance(expected, dict) and "type" in expected:
            msg = f"Expected type '{expected['type']}'. {msg}"

    return ValidationIssue(instance_path=inst or "/", schema_path=sch or "/", message=msg)


def _import_jsonschema():
    try:
        import jsonschema  # type: ignore
        return jsonschema
    except Exception as e:
        raise ValueError(
            "Dependency missing: 'jsonschema' is required to validate case-study metadata. "
            "Install with: pip install jsonschema"
        ) from e


def validate_metadata(
    metadata: Any,
    schema: Optional[Dict[str, Any]] = None,
    *,
    schema_path: Optional[Path] = None,
) -> None:
    js = _import_jsonschema()
    sch = schema if schema is not None else load_schema(schema_path=schema_path)

    try:
        validator_cls = getattr(js, "Draft202012Validator", None) or js.Draft7Validator
        validator = validator_cls(sch)
    except Exception as e:
        raise ValueError("Invalid JSON Schema: failed to initialize validator.") from e

    errors = sorted(validator.iter_errors(metadata), key=lambda er: (list(getattr(er, "absolute_path", [])), er.message))
    if not errors:
        return

    issues = [_format_jsonschema_error(e) for e in errors]
    lines: List[str] = ["Metadata validation failed:"]
    for i, issue in enumerate(issues, 1):
        lines.append(f"{i}. At {issue.instance_path}: {issue.message}")
        lines.append(f"   Schema: {issue.schema_path}")
    raise ValueError("\n".join(lines))


def validate_metadata_file(
    metadata_path: Path,
    *,
    schema_path: Optional[Path] = None,
) -> Dict[str, Any]:
    data = load_json(metadata_path)
    validate_metadata(data, schema_path=schema_path)
    if not isinstance(data, dict):
        raise ValueError(f"Metadata must be a JSON object at top level: {metadata_path}")
    return data
