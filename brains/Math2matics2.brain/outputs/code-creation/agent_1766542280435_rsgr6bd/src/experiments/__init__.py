"""Experiments package public API.

This package exposes:
- SymPy-based symbolic derivations
- NumPy/SciPy numeric runners
- Parameter sweep harness
- Plotting and I/O helpers

Imports are implemented lazily so that importing :mod:`experiments` is fast and
doesn't require heavy optional dependencies until needed.
"""
from __future__ import annotations

from importlib import import_module
from types import ModuleType
from typing import Any, Dict, Iterable, List, Tuple

__all__ = [
    # Submodules
    "symbolic",
    "numeric",
    "sweep",
    "plotting",
    "io",
    # Helpers
    "available",
]
# Map public attributes -> (module, attribute). Populated opportunistically by
# submodules to keep this initializer lightweight.
_EXPORTS: Dict[str, Tuple[str, str]] = {
    # symbolic.py (analytic derivations)
    "derive_experiment_1": ("experiments.symbolic", "derive_experiment_1"),
    "derive_experiment_2": ("experiments.symbolic", "derive_experiment_2"),
    "derive_experiment_3": ("experiments.symbolic", "derive_experiment_3"),
    "symbolic_helpers": ("experiments.symbolic", "helpers"),
    # numeric.py (numeric runners)
    "run_experiment_1": ("experiments.numeric", "run_experiment_1"),
    "run_experiment_2": ("experiments.numeric", "run_experiment_2"),
    "run_experiment_3": ("experiments.numeric", "run_experiment_3"),
    "numeric_helpers": ("experiments.numeric", "helpers"),
    # sweep.py (parameter sweeps)
    "SweepConfig": ("experiments.sweep", "SweepConfig"),
    "run_sweep": ("experiments.sweep", "run_sweep"),
    "grid": ("experiments.sweep", "grid"),
    "latin_hypercube": ("experiments.sweep", "latin_hypercube"),
    # plotting.py
    "plot_results": ("experiments.plotting", "plot_results"),
    "plot_sweep": ("experiments.plotting", "plot_sweep"),
    # io.py
    "save_results_csv": ("experiments.io", "save_results_csv"),
    "load_results_csv": ("experiments.io", "load_results_csv"),
    "save_figure": ("experiments.io", "save_figure"),
}
def _lazy_module(name: str) -> ModuleType:
    """Import and return a submodule of :mod:`experiments`."""
    return import_module(f"experiments.{name}")


def available() -> Dict[str, bool]:
    """Return availability of optional submodules (importable or not)."""
    out: Dict[str, bool] = {}
    for mod in ("symbolic", "numeric", "sweep", "plotting", "io"):
        try:
            _lazy_module(mod)
            out[mod] = True
        except Exception:
            out[mod] = False
    return out
def __getattr__(name: str) -> Any:  # PEP 562
    if name in ("symbolic", "numeric", "sweep", "plotting", "io"):
        return _lazy_module(name)
    if name in _EXPORTS:
        mod_name, attr = _EXPORTS[name]
        mod = import_module(mod_name)
        return getattr(mod, attr)
    raise AttributeError(f"module 'experiments' has no attribute {name!r}")


def __dir__() -> List[str]:
    base: Iterable[str] = globals().keys()
    return sorted(set(list(base) + list(__all__) + list(_EXPORTS.keys())))
