"""
qa: Standardized QA runner package.

This package provides the namespace for the single QA runner entrypoint
(e.g., `python -m qa.run`). The runner implementation lives in `qa.run`
and may rely on stable path utilities in `qa.paths`.

This module intentionally avoids importing heavy dependencies at import time.
"""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _pkg_version

__all__ = [
    "__version__",
    "get_version",
]


def get_version(default: str = "0.0.0") -> str:
    """Return the installed package version if available, else *default*."""
    try:
        return _pkg_version("qa")
    except PackageNotFoundError:
        return default


__version__ = get_version()
