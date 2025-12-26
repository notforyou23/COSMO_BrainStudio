"""dgpipe package.

This package provides utilities used by the generated CLI tool. The public
interface is intentionally small: consumers should rely on stable symbols
exported via ``__all__`` and the package version metadata in ``__version__``.
"""
from __future__ import annotations

from importlib import metadata as _metadata

__all__ = ["__version__", "get_version"]

# Keep the version resolution import-safe and side-effect-free.
def get_version(default: str = "0.0.0") -> str:
    """Return the installed distribution version for ``dgpipe``.

    If the package is not installed (e.g., running from a source checkout),
    ``default`` is returned.
    """
    try:
        return _metadata.version("dgpipe")
    except _metadata.PackageNotFoundError:
        return default


__version__ = get_version()
