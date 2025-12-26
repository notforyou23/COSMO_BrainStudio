from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple, Union

Json = Union[Dict[str, Any], list, str, int, float, bool, None]


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: Tuple[str, ...] = ()

    def raise_for_errors(self) -> None:
        if not self.ok:
            raise ValueError("Schema validation failed:\n- " + "\n- ".join(self.errors))


def _repo_root() -> Path:
    # src/catalog/schema.py -> src/catalog -> src -> <repo_root>
    return Path(__file__).resolve().parents[2]


def schema_path() -> Path:
    return _repo_root() / "outputs" / "catalog" / "METADATA_SCHEMA.json"


def load_schema(path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    p = Path(path) if path is not None else schema_path()
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Schema file not found: {p}") from e
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in schema file: {p}: {e}") from e


def _format_error(err: Any) -> str:
    # jsonschema.ValidationError has .message, .absolute_path, .schema_path
    msg = getattr(err, "message", None) or str(err)
    path_bits = []
    abs_path = getattr(err, "absolute_path", None)
    if abs_path:
        try:
            path_bits = list(abs_path)
        except TypeError:
            path_bits = []
    path_str = "".join(f"[{repr(p)}]" if isinstance(p, int) else f".{p}" for p in path_bits)
    path_str = path_str.lstrip(".")
    if path_str:
        return f"{path_str}: {msg}"
    return msg


def validate_json(
    doc: Json,
    schema: Optional[Dict[str, Any]] = None,
    schema_file: Optional[Union[str, Path]] = None,
) -> ValidationResult:
    schema_obj = schema if schema is not None else load_schema(schema_file)

    try:
        import jsonschema  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "jsonschema is required for validation but is not installed. "
            "Install it with: pip install jsonschema"
        ) from e

    try:
        validator_cls = jsonschema.validators.validator_for(schema_obj)
        validator_cls.check_schema(schema_obj)
        validator = validator_cls(schema_obj)
        errors = tuple(_format_error(e) for e in sorted(validator.iter_errors(doc), key=str))
        return ValidationResult(ok=(len(errors) == 0), errors=errors)
    except jsonschema.SchemaError as e:  # type: ignore[attr-defined]
        raise ValueError(f"Invalid JSON Schema: {_format_error(e)}") from e


def validate_case_study(
    case_study: Dict[str, Any],
    schema: Optional[Dict[str, Any]] = None,
    schema_file: Optional[Union[str, Path]] = None,
) -> None:
    """Validate a case-study document; raises ValueError with details on failure."""
    res = validate_json(case_study, schema=schema, schema_file=schema_file)
    res.raise_for_errors()
