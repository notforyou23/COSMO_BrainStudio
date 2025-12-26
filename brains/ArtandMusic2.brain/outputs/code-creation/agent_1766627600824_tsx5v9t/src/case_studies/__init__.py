"""
case_studies package.

This package provides versioned metadata schema utilities and lightweight
automation/validation helpers for working with case-study folders.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

__all__ = [
    "__version__",
    "LATEST_SCHEMA_VERSION",
    "SchemaValidationError",
    "get_schema",
    "validate_metadata",
    "validate_metadata_file",
]

__version__ = "0.1.0"
LATEST_SCHEMA_VERSION = 1


class SchemaValidationError(ValueError):
    """Raised when metadata fails schema validation."""

    def __init__(self, errors: Iterable[str], *, version: int = LATEST_SCHEMA_VERSION):
        self.version = int(version)
        self.errors = tuple(str(e) for e in errors)
        msg = "Schema v%s validation failed (%d error%s): %s" % (
            self.version,
            len(self.errors),
            "" if len(self.errors) == 1 else "s",
            "; ".join(self.errors),
        )
        super().__init__(msg)


def get_schema(version: int = LATEST_SCHEMA_VERSION):
    """Return a schema module/object for the requested version."""
    v = int(version)
    if v == 1:
        from . import schema_v1 as schema

        return schema
    raise ValueError(f"Unsupported schema version: {version!r}")


def validate_metadata(
    metadata: Mapping[str, Any],
    *,
    version: int = LATEST_SCHEMA_VERSION,
    strict: bool = True,
) -> Tuple[bool, Tuple[str, ...]]:
    """Validate a metadata dict against a schema version.

    Returns: (ok, errors)
    """
    schema = get_schema(version)
    ok, errors = schema.validate(metadata, strict=bool(strict))
    errors_t = tuple(errors) if errors else tuple()
    return bool(ok), errors_t


def validate_metadata_file(
    path: str | "Path",
    *,
    version: int = LATEST_SCHEMA_VERSION,
    strict: bool = True,
) -> Tuple[bool, Tuple[str, ...], Optional[Dict[str, Any]]]:
    """Load and validate a metadata JSON file. Returns (ok, errors, data)."""
    from pathlib import Path as _Path
    import json as _json

    p = _Path(path)
    try:
        data = _json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:  # pragma: no cover
        return False, (f"Failed to load JSON: {e}",), None

    ok, errors = validate_metadata(data, version=version, strict=strict)
    return ok, errors, data
