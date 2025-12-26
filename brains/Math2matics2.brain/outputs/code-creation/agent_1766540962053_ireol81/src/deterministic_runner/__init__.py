"""Deterministic runner library.

This package provides a deterministic command-line entrypoint and utilities
to make runs reproducible across Python processes.
"""
from __future__ import annotations

from importlib import metadata as _metadata
from typing import TYPE_CHECKING, Any

__all__ = [
    "__version__",
    "get_version",
    "set_deterministic",
    "run",
]

def get_version() -> str:
    """Return the installed package version.

    Falls back to ``0.0.0`` when package metadata is unavailable (e.g. when
    running from a source checkout without installation).
    """
    try:
        return _metadata.version("deterministic_runner")
    except _metadata.PackageNotFoundError:
        return "0.0.0"

__version__ = get_version()

if TYPE_CHECKING:
    # Import only for type checking to keep import side-effects minimal.
    from .cli import run  # noqa: F401
    from .determinism import set_deterministic  # noqa: F401

def __getattr__(name: str) -> Any:
    """Lazy attribute access for the public API.

    This avoids importing optional/heavy dependencies at module import time.
    """
    if name == "set_deterministic":
        from .determinism import set_deterministic as _set_deterministic

        return _set_deterministic
    if name == "run":
        from .cli import run as _run

        return _run
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
