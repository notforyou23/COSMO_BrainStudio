"""Schema validation for qg_bench datasets.

This module loads the bundled JSON Schema and validates benchmark datasets
using ``jsonschema`` with human-friendly error messages.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from importlib import resources

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
SCHEMA_RESOURCE_PACKAGE = "qg_bench.schemas"
SCHEMA_RESOURCE_NAME = "benchmark.schema.json"
@dataclass(frozen=True)
class ValidationIssue:
    """A single schema validation issue."""

    path: str
    message: str
    validator: str | None = None

    def format(self) -> str:
        v = f" ({self.validator})" if self.validator else ""
        return f"- {self.path}: {self.message}{v}"
def _json_pointer(parts: Sequence[Any]) -> str:
    # jsonschema uses deque/tuple of keys/indices; format as JSON Pointer.
    if not parts:
        return "$"
    out = "$"
    for p in parts:
        if isinstance(p, int):
            out += f"[{p}]"
        else:
            s = str(p).replace("~", "~0").replace("/", "~1")
            out += f"/{s}"
    return out
def load_schema() -> dict[str, Any]:
    """Load the bundled benchmark schema as a dict."""
    with resources.files(SCHEMA_RESOURCE_PACKAGE).joinpath(SCHEMA_RESOURCE_NAME).open(
        "r", encoding="utf-8"
    ) as f:
        return json.load(f)
def iter_validation_issues(data: Any, schema: Mapping[str, Any] | None = None) -> Iterable[ValidationIssue]:
    """Yield all validation issues (sorted, deterministic)."""
    sch = dict(schema) if schema is not None else load_schema()
    validator = Draft202012Validator(sch)
    errors = sorted(validator.iter_errors(data), key=lambda e: (list(e.path), e.message))
    for err in errors:
        yield ValidationIssue(
            path=_json_pointer(list(err.path)),
            message=err.message,
            validator=getattr(err, "validator", None),
        )
def validate_dataset(data: Any, *, schema: Mapping[str, Any] | None = None) -> None:
    """Validate a dataset object.

    Raises:
        ValueError: if validation fails, with a multi-line readable message.
    """
    issues = list(iter_validation_issues(data, schema=schema))
    if not issues:
        return
    header = f"Dataset failed schema validation with {len(issues)} error(s):"
    body = "\n".join(i.format() for i in issues[:50])
    extra = "" if len(issues) <= 50 else f"\n... and {len(issues) - 50} more"
    raise ValueError(f"{header}\n{body}{extra}")
def load_dataset(path: str | Path) -> Any:
    """Load a JSON dataset from disk."""
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Dataset file not found: {p}") from e
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        loc = f"line {e.lineno} column {e.colno}"
        raise ValueError(f"Invalid JSON in {p} ({loc}): {e.msg}") from e
def validate_file(path: str | Path, *, schema: Mapping[str, Any] | None = None) -> Any:
    """Load and validate a dataset file; returns the parsed object."""
    data = load_dataset(path)
    validate_dataset(data, schema=schema)
    return data
