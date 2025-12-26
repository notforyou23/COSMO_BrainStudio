"""Benchmark run validation helpers.

This module validates a benchmark run JSON document (loaded into a Python dict)
against the repository's JSON Schema and produces a compact, human-readable
error report suitable for CLI use.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from jsonschema import ValidationError
from jsonschema.validators import validator_for

from .schema import load_schema
@dataclass(frozen=True)
class ValidationErrorDetail:
    """A lightweight, serialisable view of a ``jsonschema`` ValidationError."""

    message: str
    instance_path: str
    schema_path: str
    validator: str
    validator_value: Any = None
def _json_pointer(path: Iterable[Union[str, int]]) -> str:
    parts: List[str] = []
    for p in path:
        s = str(p).replace("~", "~0").replace("/", "~1")
        parts.append(s)
    return "/" + "/".join(parts) if parts else "/"
def _flatten_error(err: ValidationError) -> List[ValidationError]:
    """Flatten compound errors (e.g. oneOf/anyOf) into leaf errors."""
    if err.context:
        out: List[ValidationError] = []
        for c in err.context:
            out.extend(_flatten_error(c))
        return out
    return [err]
def _to_detail(err: ValidationError) -> ValidationErrorDetail:
    return ValidationErrorDetail(
        message=err.message,
        instance_path=_json_pointer(err.path),
        schema_path=_json_pointer(err.schema_path),
        validator=str(err.validator) if err.validator is not None else "",
        validator_value=err.validator_value,
    )
def validate_run(
    run: Mapping[str, Any],
    *,
    schema: Optional[Mapping[str, Any]] = None,
) -> Tuple[bool, Sequence[ValidationErrorDetail]]:
    """Validate a benchmark run dict against the benchmark schema.

    Returns ``(ok, errors)`` where ``errors`` is a (possibly empty) list of
    :class:`ValidationErrorDetail`.
    """
    resolver = None
    if schema is None:
        schema, resolver = load_schema(return_resolver=True)  # type: ignore[misc]

    Validator = validator_for(schema)  # picks Draft based on $schema, defaults safely
    validator = Validator(schema, resolver=resolver)
    raw_errors: List[ValidationError] = []
    for e in validator.iter_errors(run):
        raw_errors.extend(_flatten_error(e))

    raw_errors.sort(key=lambda e: (list(e.path), e.message))
    details = [_to_detail(e) for e in raw_errors]
    return (len(details) == 0), details
def validate_run_file(
    path: Union[str, Path],
    *,
    schema: Optional[Mapping[str, Any]] = None,
) -> Tuple[bool, Sequence[ValidationErrorDetail], Mapping[str, Any]]:
    """Load a JSON file and validate it as a benchmark run.

    Returns ``(ok, errors, run_dict)``.
    """
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        run = json.load(f)
    ok, errors = validate_run(run, schema=schema)
    return ok, errors, run
def format_errors(
    errors: Sequence[ValidationErrorDetail],
    *,
    max_errors: Optional[int] = 50,
) -> str:
    """Format validation errors as a readable multi-line string."""
    if not errors:
        return "OK"

    shown = errors if max_errors is None else errors[:max_errors]
    lines: List[str] = []
    lines.append(f"{len(errors)} validation error(s):")
    for i, e in enumerate(shown, 1):
        loc = e.instance_path or "/"
        lines.append(f"{i:>2}. {loc}: {e.message} (schema {e.schema_path})")
    if max_errors is not None and len(errors) > max_errors:
        lines.append(f"... {len(errors) - max_errors} more not shown")
    return "\n".join(lines)
