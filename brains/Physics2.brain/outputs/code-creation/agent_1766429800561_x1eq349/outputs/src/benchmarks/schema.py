"""Schema loading and JSON Schema validation helpers.

These utilities are shared by the CLI and the automated test suite.
They intentionally keep I/O and error messages deterministic to make CI reliable.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

import json

from jsonschema import FormatChecker, ValidationError, validators
JSONMapping = Dict[str, Any]


@dataclass(frozen=True)
class SchemaValidationResult:
    """Result of a schema validation run."""

    valid: bool
    errors: List[str]
def default_schema_path(filename: str = "benchmark.schema.json") -> Path:
    """Return the default schema location within the repository layout.

    Assumes this file lives at: outputs/src/benchmarks/schema.py and the schema at
    outputs/schemas/<filename>.
    """
    outputs_dir = Path(__file__).resolve().parents[2]
    return outputs_dir / "schemas" / filename
def load_schema(path: Optional[Union[str, Path]] = None) -> JSONMapping:
    """Load and parse a JSON Schema file.

    Args:
        path: Optional path to a schema JSON file. If omitted, uses the default
            schema location.

    Raises:
        FileNotFoundError: if the schema path does not exist.
        json.JSONDecodeError: if the schema file is not valid JSON.
    """
    schema_path = Path(path) if path is not None else default_schema_path()
    text = schema_path.read_text(encoding="utf-8")
    return json.loads(text)
def _validator_for_schema(schema: JSONMapping):
    """Construct an appropriate jsonschema validator for the given schema."""
    cls = validators.validator_for(schema)
    cls.check_schema(schema)
    return cls(schema, format_checker=FormatChecker())
def iter_validation_errors(
    instance: Any,
    *,
    schema: Optional[JSONMapping] = None,
    schema_path: Optional[Union[str, Path]] = None,
) -> Iterable[ValidationError]:
    """Yield JSON Schema validation errors for an instance.

    Provide either a pre-loaded schema or a schema_path. If both are omitted,
    the default schema is used.
    """
    if schema is None:
        schema = load_schema(schema_path)
    validator = _validator_for_schema(schema)
    yield from validator.iter_errors(instance)
def validate_or_raise(
    instance: Any,
    *,
    schema: Optional[JSONMapping] = None,
    schema_path: Optional[Union[str, Path]] = None,
) -> None:
    """Validate an instance and raise the first error with a readable message."""
    errors = sorted(
        iter_validation_errors(instance, schema=schema, schema_path=schema_path),
        key=lambda e: list(e.path),
    )
    if not errors:
        return
    err = errors[0]
    loc = ".".join(str(p) for p in err.path) or "<root>"
    raise ValidationError(f"{err.message} (at {loc})")
def validate(
    instance: Any,
    *,
    schema: Optional[JSONMapping] = None,
    schema_path: Optional[Union[str, Path]] = None,
) -> SchemaValidationResult:
    """Validate an instance and return a structured result (no exception)."""
    msgs: List[str] = []
    for err in sorted(
        iter_validation_errors(instance, schema=schema, schema_path=schema_path),
        key=lambda e: (list(e.path), e.message),
    ):
        loc = ".".join(str(p) for p in err.path) or "<root>"
        msgs.append(f"{err.message} (at {loc})")
    return SchemaValidationResult(valid=not msgs, errors=msgs)
