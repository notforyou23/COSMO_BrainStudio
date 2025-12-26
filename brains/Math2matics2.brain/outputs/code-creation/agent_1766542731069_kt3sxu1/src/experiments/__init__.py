"""Experiments package.

This package provides reusable building blocks for running parameter sweeps,
persisting inputs/outputs, and plotting results.

The public API is exposed at the package root (``experiments``) while keeping
implementations in submodules:
- :mod:`experiments.io`
- :mod:`experiments.sweep`
- :mod:`experiments.plotting`

Imports are resolved lazily so importing :mod:`experiments` stays lightweight
and does not require optional heavy dependencies (e.g., plotting backends)
unless you access them.
"""

from __future__ import annotations

from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
from typing import Any

__all__ = [
    # Submodules
    "io",
    "sweep",
    "plotting",
    # Metadata
    "__version__",
]

try:
    __version__ = version("generated_script_1766542734624")
except PackageNotFoundError:  # pragma: no cover
    # When running from a source tree without an installed distribution.
    __version__ = "0.0.0"


_LAZY_SUBMODULES = ("io", "sweep", "plotting")


def __getattr__(name: str) -> Any:
    """Lazily import submodules and re-export their public symbols.

    This supports both styles:
      - ``import experiments; experiments.io``
      - ``from experiments import write_results`` (if defined in submodules)
    """
    if name in _LAZY_SUBMODULES:
        return import_module(f"{__name__}.{name}")

    # Re-export submodule attributes at package root if they exist.
    for mod_name in _LAZY_SUBMODULES:
        try:
            mod = import_module(f"{__name__}.{mod_name}")
        except ModuleNotFoundError:
            continue
        if hasattr(mod, name):
            value = getattr(mod, name)
            globals()[name] = value  # cache for future lookups
            if name not in __all__:
                __all__.append(name)
            return value

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    names = set(globals())
    for mod_name in _LAZY_SUBMODULES:
        try:
            mod = import_module(f"{__name__}.{mod_name}")
        except ModuleNotFoundError:
            continue
        names.update(getattr(mod, "__all__", ()))
        names.update(getattr(mod, "__dict__", {}).keys())
    return sorted(names)
