"""dgpipe.utils

Reusable helper utilities for dgpipe's CLI and core modules.

This module is intentionally small and dependency-light. It provides common
validation helpers, JSON helpers, and formatting/error utilities so that other
modules can stay focused on their primary responsibilities.
"""

from __future__ import annotations

from dataclasses import is_dataclass, asdict
from pathlib import Path
from typing import Any, Iterable, Mapping, MutableMapping, Optional

import json
import os
import re
class DgpipeError(Exception):
    """Base exception for dgpipe."""


class ValidationError(DgpipeError, ValueError):
    """Raised when user-supplied configuration or inputs are invalid."""


class IOError(DgpipeError):
    """Raised for dgpipe-specific IO failures."""
_IDENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def ensure(condition: bool, message: str, *, exc: type[Exception] = ValidationError) -> None:
    """Raise *exc* with *message* if *condition* is falsy."""
    if not condition:
        raise exc(message)


def validate_identifier(value: str, *, what: str = "identifier") -> str:
    """Validate and return a stable identifier (e.g., stage/pipeline name)."""
    ensure(isinstance(value, str), f"{what} must be a string")
    ensure(value.strip() == value and value, f"{what} must be non-empty and trimmed")
    ensure(_IDENT_RE.match(value) is not None, f"Invalid {what}: {value!r}")
    return value


def require_keys(d: Mapping[str, Any], keys: Iterable[str], *, what: str = "mapping") -> None:
    """Validate that *d* contains all required keys."""
    missing = [k for k in keys if k not in d]
    ensure(not missing, f"{what} missing required keys: {missing}")
def coerce_path(value: str | os.PathLike[str] | Path, *, expand: bool = True) -> Path:
    """Convert a path-like to :class:`~pathlib.Path`.

    If *expand* is True, user home and environment variables are expanded.
    """
    p = Path(value)
    if expand:
        p = Path(os.path.expandvars(os.path.expanduser(str(p))))
    return p


def ensure_dir(path: str | os.PathLike[str] | Path) -> Path:
    """Create *path* as a directory if it doesn't exist; return as Path."""
    p = coerce_path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
def _to_jsonable(obj: Any) -> Any:
    """Best-effort conversion for JSON serialization."""
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, Path):
        return str(obj)
    return obj


def json_dumps(obj: Any, *, indent: int = 2, sort_keys: bool = True) -> str:
    """Serialize *obj* to JSON with stable defaults."""
    return json.dumps(
        obj,
        default=_to_jsonable,
        indent=indent,
        sort_keys=sort_keys,
        ensure_ascii=False,
    )


def read_json(path: str | os.PathLike[str] | Path) -> Any:
    """Read JSON from *path* and return the decoded value."""
    p = coerce_path(path)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise IOError(f"JSON file not found: {p}") from e
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON in {p}: {e}") from e


def write_json(path: str | os.PathLike[str] | Path, value: Any) -> Path:
    """Write *value* as JSON to *path* (UTF-8) and return the path."""
    p = coerce_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json_dumps(value) + "\n", encoding="utf-8")
    return p
def format_exception(exc: BaseException) -> str:
    """Return a concise, user-facing error message for an exception."""
    msg = str(exc).strip()
    name = type(exc).__name__
    return f"{name}: {msg}" if msg else name


def format_kv(fields: Mapping[str, Any], *, sep: str = ", ") -> str:
    """Format a mapping as stable key=value pairs for logs."""
    items = []
    for k in sorted(fields.keys()):
        v = fields[k]
        items.append(f"{k}={v!r}")
    return sep.join(items)


def merge_dicts(base: Mapping[str, Any], updates: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    """Shallow-merge two mappings into a new dict (updates override base)."""
    out: dict[str, Any] = dict(base)
    if updates:
        out.update(dict(updates))
    return out
