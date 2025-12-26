"""Benchmarks package.

This package is intentionally lightweight: it provides stable import paths for
benchmark computation and schema validation utilities that live under
``outputs/src/benchmarks``.

The test/CI scaffolding added elsewhere in the repository can rely on these
imports without forcing heavy dependencies to import at package import time.
"""

from __future__ import annotations

from importlib import import_module
from types import ModuleType
from typing import Any, Optional

__all__ = [
    "optional_import",
    "load_module",
    "schema",
    "compute",
    "validate",
]

def optional_import(module: str) -> Optional[ModuleType]:
    """Import *module* relative to this package and return it or ``None``.

    This keeps ``benchmarks`` importable even when only a subset of modules is
    present (e.g., during incremental generation stages).
    """
    try:
        return import_module(f"{__name__}.{module}")
    except ModuleNotFoundError:
        return None

def load_module(module: str) -> ModuleType:
    """Import *module* relative to this package, raising on failure."""
    return import_module(f"{__name__}.{module}")

# Common submodules (if/when they exist).
schema = optional_import("schema")
compute = optional_import("compute")
validate = optional_import("validate")

def __getattr__(name: str) -> Any:  # pragma: no cover
    """Lazy attribute access for submodules and their public members.

    Examples:
        - ``from benchmarks import compute`` (module)
        - ``from benchmarks import run`` (member of ``benchmarks.compute``)
    """
    if name in {"schema", "compute", "validate"}:
        return globals()[name]
    for mod in (compute, validate, schema):
        if mod is not None and hasattr(mod, name):
            return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
