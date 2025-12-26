"""Schema utilities.

Provides:
- Loading JSON / JSON Schema from disk.
- Resolving *local* ($ref starting with "#/") references into an inline schema.
- Draft 2020-12 validation with stable, readable error reporting.

These helpers are intentionally small and dependency-light; they only assume
`jsonschema` is installed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Tuple

import copy
import json

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
def load_json(path: Path) -> Any:
    """Load a JSON file with UTF-8 encoding."""
    return json.loads(path.read_text(encoding="utf-8"))


def _decode_json_pointer_part(part: str) -> str:
    # RFC 6901: "~1" => "/", "~0" => "~"
    return part.replace("~1", "/").replace("~0", "~")


def _get_by_json_pointer(doc: Any, ref: str) -> Any:
    """Resolve a local JSON pointer like '#/a/b/0'."""
    if not ref.startswith("#"):
        raise ValueError(f"Only local refs are supported, got: {ref!r}")
    pointer = ref[1:]
    if pointer in ("", "/"):
        return doc
    if not pointer.startswith("/"):
        raise ValueError(f"Invalid JSON pointer in ref: {ref!r}")
    cur = doc
    for raw in pointer.lstrip("/").split("/"):
        part = _decode_json_pointer_part(raw)
        if isinstance(cur, list):
            cur = cur[int(part)]
        else:
            cur = cur[part]
    return cur
def resolve_local_refs(schema: Mapping[str, Any]) -> Dict[str, Any]:
    """Return a deep-copied schema with local '#/..' $ref inlined.

    Notes:
    - Only resolves references within the same document.
    - If an object contains "$ref" plus sibling keys, siblings override the
      referenced schema (useful for narrowing constraints in place).
    - Cycles are not expanded infinitely; a previously-expanded ref is reused.
    """
    root: Any = copy.deepcopy(schema)
    cache: Dict[str, Any] = {}

    def _walk(node: Any) -> Any:
        if isinstance(node, list):
            return [_walk(v) for v in node]
        if not isinstance(node, dict):
            return node

        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/"):
            if ref in cache:
                base = copy.deepcopy(cache[ref])
            else:
                base = _walk(copy.deepcopy(_get_by_json_pointer(root, ref)))
                cache[ref] = copy.deepcopy(base)
            # Siblings override referenced schema (except $ref itself).
            siblings = {k: _walk(v) for k, v in node.items() if k != "$ref"}
            if siblings and isinstance(base, dict):
                merged = dict(base)
                merged.update(siblings)
                return merged
            return base

        return {k: _walk(v) for k, v in node.items()}

    resolved = _walk(root)
    if not isinstance(resolved, dict):
        raise ValueError("Schema root must be an object")
    return resolved
@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str
    validator: str

    @staticmethod
    def from_error(err: ValidationError) -> "ValidationIssue":
        path = "/" + "/".join(str(p) for p in err.path) if err.path else "/"
        return ValidationIssue(path=path, message=err.message, validator=err.validator or "unknown")


def iter_validation_issues(validator: Draft202012Validator, instance: Any) -> List[ValidationIssue]:
    errors = list(validator.iter_errors(instance))
    # Stable ordering: (path, validator, message)
    issues = [ValidationIssue.from_error(e) for e in errors]
    issues.sort(key=lambda i: (i.path, i.validator, i.message))
    return issues


def format_issues(issues: Iterable[ValidationIssue], *, header: str = "Schema validation failed") -> str:
    items = list(issues)
    if not items:
        return header + ": <no issues>"
    lines = [f"{header} ({len(items)} issue(s)):"]
    for i, it in enumerate(items, 1):
        lines.append(f"  {i}. {it.path}: {it.message} [{it.validator}]")
    return "\n".join(lines)
def load_schema(schema_path: Path, *, resolve_refs: bool = True) -> Dict[str, Any]:
    """Load a JSON schema from disk, optionally inlining local refs."""
    schema = load_json(schema_path)
    if not isinstance(schema, dict):
        raise ValueError(f"Schema must be an object: {schema_path}")
    return resolve_local_refs(schema) if resolve_refs else schema


def validate_instance(instance: Any, schema: Mapping[str, Any], *, schema_name: str = "schema") -> None:
    """Validate an instance; raise ValueError with readable issues on failure."""
    validator = Draft202012Validator(schema)
    issues = iter_validation_issues(validator, instance)
    if issues:
        raise ValueError(format_issues(issues, header=f"{schema_name} validation failed"))


def validate_json_file(json_path: Path, schema: Mapping[str, Any], *, schema_name: str = "schema") -> None:
    """Load a JSON file and validate it against a schema."""
    instance = load_json(json_path)
    try:
        validate_instance(instance, schema, schema_name=schema_name)
    except ValueError as e:
        raise ValueError(f"{json_path}: {e}") from None
