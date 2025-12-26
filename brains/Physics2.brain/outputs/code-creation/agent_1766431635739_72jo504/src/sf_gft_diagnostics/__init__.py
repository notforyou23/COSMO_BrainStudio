"""sf_gft_diagnostics

Continuum-recovery diagnostics and cross-validation utilities for spin-foam / GFT
renormalization studies.

The package is organized around four submodules:

- ``observables``: catalog + estimators for candidate continuum observables and
  scaling quantities.
- ``scaling``: effective exponents, finite-size scaling collapses, bootstrap/error
  propagation helpers.
- ``metrics``: mutually comparable distances/consistency metrics for RG flows and
  semiclassical benchmarks.
- ``rg_io``: lightweight adapters/loaders to unify tensor-network/lattice RG
  outputs and spin-foam/GFT coarse-graining logs.

This ``__init__`` exposes a small, stable public API while remaining robust when
optional submodules are not yet available (e.g., during staged development).
"""
from __future__ import annotations

from importlib import import_module
from types import ModuleType
from typing import Iterable, List, Optional

__all__: List[str] = []
__version__ = "0.1.0"
def _safe_import(module: str, names: Optional[Iterable[str]] = None) -> Optional[ModuleType]:
    """Import *module* and optionally re-export *names* into this namespace.

    The import is best-effort: if the module does not exist (e.g., in a partial
    install), this function returns ``None`` without raising. If the module is
    present but a requested symbol is missing, the underlying ``AttributeError``
    is raised to surface API mismatches early.
    """
    try:
        mod = import_module(f"{__name__}.{module}")
    except ModuleNotFoundError:
        return None

    if names is None:
        return mod

    g = globals()
    for name in names:
        g[name] = getattr(mod, name)
        if name not in __all__:
            __all__.append(name)
    return mod
# Public re-exports (best-effort; submodules may be added in later stages).
_safe_import(
    "observables",
    names=[
        "ObservableSpec",
        "ObservableCatalog",
        "DEFAULT_CATALOG",
        "estimate_observable",
        "list_observables",
    ],
)

_safe_import(
    "scaling",
    names=[
        "effective_exponent",
        "finite_size_collapse",
        "hyperscaling_check",
        "bootstrap_ci",
        "propagate_errors",
    ],
)

_safe_import(
    "metrics",
    names=[
        "js_distance",
        "wasserstein_distance",
        "kl_divergence_surrogate",
        "curve_distance",
        "trajectory_distance",
        "consistency_score",
    ],
)

_safe_import(
    "rg_io",
    names=[
        "RGDataset",
        "load_rg_dataset",
        "from_tensor_network_rg",
        "from_gft_coarse_graining_log",
    ],
)
def available_symbols() -> List[str]:
    """Return a sorted list of public API symbols that are currently available."""
    return sorted(__all__)


def __getattr__(name: str):
    """Lazy attribute resolution for submodule members.

    This enables ``sf_gft_diagnostics.metrics`` etc. even when only the package
    is imported. If a requested attribute matches a known submodule name, the
    submodule is imported and returned.
    """
    if name in {"observables", "scaling", "metrics", "rg_io"}:
        return import_module(f"{__name__}.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
