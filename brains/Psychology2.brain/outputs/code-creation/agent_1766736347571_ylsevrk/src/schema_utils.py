"""JSON Schema loading and validation utilities.

Features:
- Load schemas from local paths with support for local $ref resolution.
- Friendly error formatting for jsonschema validation errors.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union
import json

try:
    import jsonschema
    from jsonschema import Draft202012Validator
except Exception as e:  # pragma: no cover
    raise RuntimeError("jsonschema is required (pip install jsonschema)") from e
PathLike = Union[str, Path]

def _as_path(p: PathLike) -> Path:
    return p if isinstance(p, Path) else Path(p)

def _file_uri(path: Path) -> str:
    return path.resolve().as_uri()

def load_json(path: PathLike) -> Any:
    path = _as_path(path)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def _collect_local_schemas(root: Path) -> Dict[str, Any]:
    store: Dict[str, Any] = {}
    root = root.resolve()
    if root.is_dir():
        candidates = list(root.rglob("*.json"))
    else:
        candidates = [root]
    for p in candidates:
        try:
            data = load_json(p)
        except Exception:
            continue
        store[_file_uri(p)] = data
    return store
def load_schema(schema_path: PathLike, codebook_path: Optional[PathLike] = None) -> Dict[str, Any]:
    """Load a JSON Schema and prepare it for local reference resolution.

    If codebook_path is provided, it is added to the resolver store so that
    schemas can $ref it by relative path or by its file:// URI.
    """
    schema_path = _as_path(schema_path).resolve()
    schema = load_json(schema_path)

    store = _collect_local_schemas(schema_path.parent)
    if codebook_path is not None:
        cb_path = _as_path(codebook_path).resolve()
        try:
            cb = load_json(cb_path)
            store[_file_uri(cb_path)] = cb
        except Exception:
            pass

    # Ensure the schema itself is addressable by absolute file URI.
    store[_file_uri(schema_path)] = schema
    schema.setdefault("$id", _file_uri(schema_path))
    schema["_local_store"] = store  # used by make_validator()
    return schema

def make_validator(schema: Dict[str, Any]) -> Draft202012Validator:
    store = dict(schema.get("_local_store", {}))
    base_uri = schema.get("$id") or ""
    resolver = jsonschema.RefResolver(base_uri=base_uri, referrer=schema, store=store)
    return Draft202012Validator(schema, resolver=resolver)
def _json_pointer(parts: Iterable[Union[str, int]]) -> str:
    def esc(s: str) -> str:
        return s.replace("~", "~0").replace("/", "~1")
    out = ""
    for p in parts:
        out += "/" + esc(str(p))
    return out or "/"

def format_error(err: "jsonschema.ValidationError") -> str:
    path = _json_pointer(err.absolute_path)
    schema_path = _json_pointer(err.absolute_schema_path)
    msg = err.message

    extra = []
    if err.validator == "required" and isinstance(err.validator_value, list):
        missing = ""
        if isinstance(err.message, str) and "'" in err.message:
            missing = err.message.split("'")[1]
        if missing:
            extra.append(f"missing={missing}")
    if err.validator in ("enum", "const"):
        extra.append(f"allowed={err.validator_value}")
    if err.validator == "type":
        extra.append(f"expected={err.validator_value}")

    suffix = f" ({', '.join(extra)})" if extra else ""
    return f"{path}: {msg}{suffix} [schema{schema_path}]"

@dataclass
class ValidationResult:
    ok: bool
    errors: List[str]
def validate_instance(instance: Any, schema: Dict[str, Any]) -> ValidationResult:
    v = make_validator(schema)
    errs = sorted(v.iter_errors(instance), key=lambda e: (list(e.absolute_path), list(e.absolute_schema_path)))
    formatted = [format_error(e) for e in errs]
    return ValidationResult(ok=(len(formatted) == 0), errors=formatted)

def validate_file(data_path: PathLike, schema_path: PathLike, codebook_path: Optional[PathLike] = None) -> ValidationResult:
    data_path = _as_path(data_path)
    data = load_json(data_path)
    schema = load_schema(schema_path, codebook_path=codebook_path)
    return validate_instance(data, schema)

def validate_jsonl_lines(lines: Iterable[str], schema: Dict[str, Any]) -> ValidationResult:
    v = make_validator(schema)
    errors: List[str] = []
    for i, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception as e:
            errors.append(f"/: invalid JSON on line {i}: {e}")
            continue
        for err in sorted(v.iter_errors(obj), key=lambda e: (list(e.absolute_path), list(e.absolute_schema_path))):
            errors.append(f"line {i} " + format_error(err))
    return ValidationResult(ok=(len(errors) == 0), errors=errors)
