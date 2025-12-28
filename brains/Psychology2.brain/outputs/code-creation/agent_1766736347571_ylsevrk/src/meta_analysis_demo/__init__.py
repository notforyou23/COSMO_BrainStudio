"""Meta-analysis starter-kit demo package.

This package is designed to support an end-to-end, reproducible meta-analysis demo:
- Load a toy CSV input dataset
- Compute effect sizes and fixed/random effects pooling
- Write standardized tabular outputs and logs to outputs/ and _build/
- Generate at least one saved figure (e.g., a forest plot)

The public API is kept small and import-safe (lazy) so importing the package does not
require optional analysis/plotting dependencies until you actually call into them.
"""
from __future__ import annotations

from importlib import import_module
from typing import Any


__all__ = [
    "__version__",
    "run_demo",
    "meta",
    "io_utils",
    "plotting",
]

__version__ = "0.1.0"


_LAZY_ATTRS = {
    # module alias -> submodule path
    "run_demo": "meta_analysis_demo.run_demo",
    "meta": "meta_analysis_demo.meta",
    "io_utils": "meta_analysis_demo.io_utils",
    "plotting": "meta_analysis_demo.plotting",
}


def __getattr__(name: str) -> Any:
    """Lazy-load key submodules to keep imports fast and robust."""
    if name in _LAZY_ATTRS:
        mod = import_module(_LAZY_ATTRS[name])
        globals()[name] = mod
        return mod
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(list(globals().keys()) + list(_LAZY_ATTRS.keys())))
