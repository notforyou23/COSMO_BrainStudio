"""Experiments package.

This package is intentionally lightweight at import time. The registry implementation
lives in :mod:`experiments.registry` and is loaded lazily to avoid import-time side
effects and to keep CLI/module import smoke-tests fast and reliable.

Public API is exposed via attribute access (PEP 562) and a small set of helper
functions that import the registry module only when needed.
"""
from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any, List
if TYPE_CHECKING:  # pragma: no cover
    # Imported only for static type checking; runtime import is lazy.
    from . import registry as registry  # noqa: F401
__all__ = [
    "get_registry",
    # Common registry symbols (resolved lazily via __getattr__):
    "registry",
    "ExperimentRegistry",
    "Registry",
    "register",
    "get",
    "list_experiments",
]
_LAZY_EXPORTS = {
    "registry",
    "ExperimentRegistry",
    "Registry",
    "register",
    "get",
    "list_experiments",
}
def _load_registry_module():
    """Import and return :mod:`experiments.registry`."""
    return import_module(__name__ + ".registry")
def get_registry():
    """Return the registry module (:mod:`experiments.registry`) lazily."""
    return _load_registry_module()
def __getattr__(name: str) -> Any:  # pragma: no cover
    """Lazily resolve registry symbols from :mod:`experiments.registry`."""
    if name in _LAZY_EXPORTS:
        mod = _load_registry_module()
        return mod if name == "registry" else getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
def __dir__() -> List[str]:  # pragma: no cover
    return sorted(set(globals().keys()) | _LAZY_EXPORTS)
