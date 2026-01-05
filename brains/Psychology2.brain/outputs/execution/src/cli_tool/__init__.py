"""cli_tool package.

This module defines the public surface for the project: package versioning and
canonical entrypoints used by the CLI and runner.
"""

from __future__ import annotations

from importlib import metadata as _metadata
from typing import Any as _Any

try:
    __version__ = _metadata.version("cli_tool")
except _metadata.PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"


__all__ = [
    "__version__",
    "app",
    "run",
]


def __getattr__(name: str) -> _Any:
    """Lazy-load canonical entrypoints to avoid import-order side effects."""
    if name == "app":
        from .cli import app as _app

        return _app
    if name == "run":
        from .runner import run as _run

        return _run
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
