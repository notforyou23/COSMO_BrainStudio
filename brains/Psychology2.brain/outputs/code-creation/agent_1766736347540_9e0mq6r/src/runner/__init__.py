"""
Canonical runner package.

This package provides a single, stable runner entrypoint interface and related
utilities. The actual implementation lives in sibling modules (e.g.
runner.entrypoint) and is re-exported here for a consistent import path.

This initializer is intentionally lightweight and uses lazy imports so it can be
imported even when only a subset of modules are present.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any, Optional

__all__ = [
    "main",
    "run",
    "get_entrypoint",
]

__version__ = "0.1.0"
def get_entrypoint():
    """Return the canonical entrypoint module (runner.entrypoint)."""
    return import_module(__name__ + ".entrypoint")


def main(argv: Optional[list[str]] = None) -> int:
    """Invoke the canonical runner entrypoint.

    Args:
        argv: Optional argv list (excluding program name). If None, the
            entrypoint is responsible for using sys.argv.

    Returns:
        Process exit code.
    """
    ep = get_entrypoint()
    fn = getattr(ep, "main", None)
    if not callable(fn):
        raise RuntimeError("runner.entrypoint.main is not available or not callable")
    return int(fn(argv))


def run(*args: Any, **kwargs: Any) -> Any:
    """Convenience wrapper for runner.entrypoint.run if provided."""
    ep = get_entrypoint()
    fn = getattr(ep, "run", None)
    if not callable(fn):
        raise RuntimeError("runner.entrypoint.run is not available or not callable")
    return fn(*args, **kwargs)
if TYPE_CHECKING:
    # Optional re-exports for type checking; these modules may be created later.
    from .entrypoint import main as _main  # noqa: F401
