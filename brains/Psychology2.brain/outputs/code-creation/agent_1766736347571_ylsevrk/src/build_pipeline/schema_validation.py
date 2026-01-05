from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
import json


class SchemaValidationError(ValueError):
    """Raised when schema validation fails (fail-fast by default)."""


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    data_path: Path
    schema_path: Path
    ok: bool
    issues: Tuple[ValidationIssue, ...]
    data: Optional[Any] = None


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise SchemaValidationError(f"Missing file: {path}") from e
    except json.JSONDecodeError as e:
        raise SchemaValidationError(f"Invalid JSON in {path}: {e}") from e


def load_schema(schema_path: Path) -> Dict[str, Any]:
    schema = _load_json(schema_path)
    if not isinstance(schema, dict):
        raise SchemaValidationError(f"Schema must be a JSON object: {schema_path}")
    return schema


def _js_type_ok(value: Any, typ: str) -> bool:
    if typ == "object":
        return isinstance(value, dict)
    if typ == "array":
        return isinstance(value, list)
    if typ == "string":
        return isinstance(value, str)
    if typ == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if typ == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if typ == "boolean":
        return isinstance(value, bool)
    if typ == "null":
        return value is None
    return True  # unknown type -> do not block


def _validate_basic(schema: Dict[str, Any], data: Any, path: str = "$") -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []

    typ = schema.get("type")
    if isinstance(typ, str):
        if not _js_type_ok(data, typ):
            issues.append(ValidationIssue(path, f"Expected {typ}, got {type(data).__name__}"))
            return issues
    elif isinstance(typ, list):
        if not any(_js_type_ok(data, t) for t in typ if isinstance(t, str)):
            issues.append(ValidationIssue(path, f"Type mismatch; expected one of {typ}"))
            return issues

    enum = schema.get("enum")
    if isinstance(enum, list) and data not in enum:
        issues.append(ValidationIssue(path, f"Value not in enum: {data!r}"))
        return issues

    if isinstance(data, dict):
        req = schema.get("required")
        if isinstance(req, list):
            for k in req:
                if isinstance(k, str) and k not in data:
                    issues.append(ValidationIssue(path, f"Missing required property: {k}"))

        props = schema.get("properties")
        if isinstance(props, dict):
            for k, subschema in props.items():
                if k in data and isinstance(subschema, dict):
                    issues.extend(_validate_basic(subschema, data[k], f"{path}.{k}"))

    if isinstance(data, list):
        items = schema.get("items")
        if isinstance(items, dict):
            for i, v in enumerate(data):
                issues.extend(_validate_basic(items, v, f"{path}[{i}]"))

    return issues


def validate_data(
    data: Any,
    schema: Dict[str, Any],
    *,
    fail_fast: bool = True,
) -> Tuple[bool, Tuple[ValidationIssue, ...]]:
    """Validate data against a JSON schema; uses jsonschema if available, else a minimal validator."""
    try:
        import jsonschema  # type: ignore

        validator = jsonschema.Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
        issues = tuple(
            ValidationIssue(
                "$" + "".join(f"[{p}]" if isinstance(p, int) else f".{p}" for p in e.absolute_path),
                e.message,
            )
            for e in errors
        )
        ok = not issues
    except Exception:
        issues = tuple(_validate_basic(schema, data))
        ok = not issues

    if not ok and fail_fast:
        msg = "; ".join(f"{i.path}: {i.message}" for i in issues[:5])
        if len(issues) > 5:
            msg += f"; (+{len(issues) - 5} more)"
        raise SchemaValidationError(msg)
    return ok, issues


def validate_file(
    data_path: Path,
    schema_path: Path,
    *,
    fail_fast: bool = True,
    return_data: bool = True,
) -> ValidationResult:
    schema = load_schema(schema_path)
    data = _load_json(data_path)
    ok, issues = validate_data(data, schema, fail_fast=fail_fast)
    return ValidationResult(data_path=data_path, schema_path=schema_path, ok=ok, issues=issues, data=data if return_data else None)


def validate_files(
    pairs: Sequence[Tuple[Path, Path]],
    *,
    fail_fast: bool = True,
    return_data: bool = True,
) -> List[ValidationResult]:
    results: List[ValidationResult] = []
    for data_path, schema_path in pairs:
        res = validate_file(data_path, schema_path, fail_fast=fail_fast, return_data=return_data)
        results.append(res)
    return results
