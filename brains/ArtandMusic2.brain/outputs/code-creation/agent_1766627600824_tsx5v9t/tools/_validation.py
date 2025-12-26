"""JSON Schema validation utilities used by the metadata CLI.

This module provides:
- validate_instance(): validate a Python object against a JSON Schema
- format_errors(): human-readable formatting for jsonschema errors
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List, Optional

try:
    import jsonschema
    from jsonschema import FormatChecker
except Exception as e:  # pragma: no cover
    raise RuntimeError("jsonschema is required for validation") from e
@dataclass(frozen=True)
class ValidationIssue:
    pointer: str
    message: str
    validator: str
    schema_path: str

    def render(self) -> str:
        where = self.pointer or "/"
        return f"{where}: {self.message} (rule={self.validator}, schema={self.schema_path})"


def _json_pointer(path: Iterable[Any]) -> str:
    parts = []
    for p in path:
        s = str(p).replace("~", "~0").replace("/", "~1")
        parts.append(s)
    return "/" + "/".join(parts) if parts else ""


def _schema_pointer(path: Iterable[Any]) -> str:
    parts = []
    for p in path:
        s = str(p).replace("~", "~0").replace("/", "~1")
        parts.append(s)
    return "#/" + "/".join(parts) if parts else "#"


def _validator_for(schema: dict) -> "jsonschema.Validator":
    # Prefer modern drafts when available, but remain compatible across environments.
    vcls = None
    for cls_name in ("Draft202012Validator", "Draft201909Validator", "Draft7Validator"):
        vcls = getattr(jsonschema, cls_name, None)
        if vcls:
            break
    if not vcls:  # pragma: no cover
        raise RuntimeError("No supported jsonschema validator class found")
    return vcls(schema, format_checker=FormatChecker())
def validate_instance(instance: Any, schema: dict) -> List[ValidationIssue]:
    """Validate instance against schema; returns a list of issues (empty if valid)."""
    validator = _validator_for(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: (list(e.absolute_path), e.message))
    issues: List[ValidationIssue] = []
    for e in errors:
        pointer = _json_pointer(e.absolute_path)
        schema_ptr = _schema_pointer(e.absolute_schema_path)
        msg = _enhance_message(e)
        issues.append(
            ValidationIssue(
                pointer=pointer,
                message=msg,
                validator=getattr(e, "validator", "unknown") or "unknown",
                schema_path=schema_ptr,
            )
        )
    return issues


def _type_name(x: Any) -> str:
    if x is None:
        return "null"
    t = type(x)
    if t is bool:
        return "boolean"
    if t is int:
        return "integer"
    if t is float:
        return "number"
    if t is str:
        return "string"
    if t is list:
        return "array"
    if t is dict:
        return "object"
    return t.__name__


def _enhance_message(err: Any) -> str:
    # Add compact context for common validators.
    v = getattr(err, "validator", None)
    if v in ("required",) and isinstance(getattr(err, "validator_value", None), (list, tuple)):
        miss = ", ".join(map(str, err.validator_value))
        return f"missing required field(s): {miss}"
    if v in ("type",) and hasattr(err, "validator_value"):
        exp = err.validator_value
        if isinstance(exp, (list, tuple)):
            exp_s = ", ".join(map(str, exp))
        else:
            exp_s = str(exp)
        return f"expected type {exp_s}, got {_type_name(getattr(err, 'instance', None))}"
    if v in ("enum",) and hasattr(err, "validator_value"):
        return f"value must be one of {list(err.validator_value)!r}"
    if v in ("additionalProperties",) and hasattr(err, "message"):
        return err.message
    return getattr(err, "message", str(err))


def format_errors(issues: List[ValidationIssue], max_items: Optional[int] = 50) -> str:
    if not issues:
        return ""
    head = f"Validation failed with {len(issues)} issue(s):"
    lines = [head]
    show = issues[: (max_items or len(issues))]
    for i, it in enumerate(show, 1):
        lines.append(f"  {i}. {it.render()}")
    if max_items and len(issues) > max_items:
        lines.append(f"  ... and {len(issues) - max_items} more")
    return "\n".join(lines) + "\n"
