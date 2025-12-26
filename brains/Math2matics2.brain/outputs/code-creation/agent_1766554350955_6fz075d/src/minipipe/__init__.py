"""minipipe: a minimal, CI-friendly pipeline package.

The package provides a deterministic pipeline (see :mod:`minipipe.pipeline`) and a
module entrypoint (see :mod:`minipipe.run`) for execution via:
    python -m minipipe.run
"""
from __future__ import annotations

from importlib import metadata as _metadata


def _detect_version() -> str:
    """Return the installed package version if available, else a dev fallback."""
    try:
        return _metadata.version("minipipe")
    except _metadata.PackageNotFoundError:
        return "0.0.0+local"


__version__ = _detect_version()

__all__ = ["__version__"]
