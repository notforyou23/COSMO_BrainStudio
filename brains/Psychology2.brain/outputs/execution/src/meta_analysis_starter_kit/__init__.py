"""
meta_analysis_starter_kit

Lightweight tooling to bootstrap a meta-analysis project: generate standard CSV
templates (extraction + screening log), run a minimal analysis workflow, and
persist run logs/outputs.

Public API is intentionally small; modules provide the implementation.
"""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _pkg_version

__all__ = [
    "__version__",
    "get_version",
]

try:
    __version__ = _pkg_version("meta_analysis_starter_kit")
except PackageNotFoundError:  # running from source tree
    __version__ = "0.1.0"

def get_version() -> str:
    """Return the installed package version (or the source fallback)."""
    return __version__
# Optional convenience re-exports (kept lazy to avoid import-time side effects).
def __getattr__(name: str):
    if name in {"config", "templates", "analysis", "logging_utils"}:
        import importlib

        return importlib.import_module(f"{__name__}.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
