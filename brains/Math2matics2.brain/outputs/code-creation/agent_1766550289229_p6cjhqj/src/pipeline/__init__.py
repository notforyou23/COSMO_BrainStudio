"""
pipeline package

This package hosts the documentation-and-research pipeline modules used by the
project's outputs-first workflow (captured logs/results, roadmap generation,
bibliography system, and coverage matrix artifacts).

The package initializer is intentionally lightweight and stable:
- exposes package metadata
- provides safe, lazy attribute access to common public helpers
- avoids importing heavy dependencies at import-time
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "atomic_write_text",
    "ensure_dir",
    "timestamp_utc",
    "normalize_bibtex",
    "validate_bibtex",
    "generate_roadmap_markdown",
]


_LAZY_ATTRS = {
    # io_utils
    "atomic_write_text": ("pipeline.io_utils", "atomic_write_text"),
    "ensure_dir": ("pipeline.io_utils", "ensure_dir"),
    "timestamp_utc": ("pipeline.io_utils", "timestamp_utc"),
    # bibliography
    "normalize_bibtex": ("pipeline.bibliography", "normalize_bibtex"),
    "validate_bibtex": ("pipeline.bibliography", "validate_bibtex"),
    # roadmap
    "generate_roadmap_markdown": ("pipeline.roadmap", "generate_roadmap_markdown"),
}


def __getattr__(name: str) -> Any:
    """Lazy-load selected public helpers.

    Keeps package import fast and prevents unintended side effects during CLI and
    test discovery. Raises AttributeError for unknown names (PEP 562).
    """
    spec = _LAZY_ATTRS.get(name)
    if not spec:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    mod_name, attr_name = spec
    mod = import_module(mod_name)
    value = getattr(mod, attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(list(globals().keys()) + list(_LAZY_ATTRS.keys())))
