"""dgpipe: Discrete-gravity pipeline.

This package provides a theoretical-to-experimental pipeline connecting
discrete-gravity microstructure models (e.g., causal sets / discrete spectra)
to measurable correlators, entanglement diagnostics, simulations, and inference.

The public API is intentionally small; internal modules may evolve while this
surface remains stable.
"""
from __future__ import annotations

from importlib import metadata as _metadata

__all__ = [
    "__version__",
    "get_version",
]
def get_version(dist_name: str = "dgpipe") -> str:
    """Return the installed package version.

    Uses importlib.metadata and falls back to a local development identifier
    when the package is not installed (e.g., running from a source checkout).
    """
    try:
        return _metadata.version(dist_name)
    except _metadata.PackageNotFoundError:
        return "0+unknown"
# Centralized version string for downstream consumers.
__version__ = get_version()
