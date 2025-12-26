"""Minimal benchmarks reference implementation.

Public API:
- load_schema(): load the benchmark JSON Schema bundled with the package.
- validate_run(): validate a benchmark run (Python dict) against the schema.
- validate_run_file(): validate a JSON file on disk.
- format_errors(): convert jsonschema errors into a readable report.

The heavy lifting lives in :mod:`benchmarks.schema` and :mod:`benchmarks.validate`.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional, Sequence, Tuple

__all__ = [
    "load_schema",
    "validate_run",
    "validate_run_file",
    "format_errors",
    "ValidationErrorDetail",
]
# Re-export the stable surface area from submodules.
from .schema import load_schema
from .validate import (
    ValidationErrorDetail,
    format_errors,
    validate_run,
    validate_run_file,
)
def validate(
    run: Mapping[str, Any],
    *,
    schema: Optional[Mapping[str, Any]] = None,
    raise_on_error: bool = False,
) -> Tuple[bool, Sequence[ValidationErrorDetail]]:
    """Backward-compatible convenience wrapper for :func:`validate_run`.

    Returns ``(ok, errors)``. If ``raise_on_error`` is True, a ``ValueError`` is
    raised with a formatted error report when validation fails.
    """
    ok, errors = validate_run(run, schema=schema)
    if (not ok) and raise_on_error:
        raise ValueError(format_errors(errors))
    return ok, errors
