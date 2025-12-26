"""Reusable experiment utilities.

This package provides small, dependency-light building blocks for running
experiments (configuration, IO, parameter sweeps, and plotting). The public API
is exposed from this module to keep imports stable for downstream users.

The implementation uses lazy attribute access (PEP 562) so importing
``experiments`` does not import optional/heavy dependencies (e.g., matplotlib).
"""
from __future__ import annotations

from importlib import import_module
from typing import Dict, Tuple
# Public symbols are defined as a mapping from name -> (module, attribute).
# This keeps the import surface stable while avoiding eager imports.
_EXPORTS: Dict[str, Tuple[str, str]] = {
    # common.py
    "set_global_seed": (".common", "set_global_seed"),
    "ensure_json_serializable": (".common", "ensure_json_serializable"),
    "now_timestamp": (".common", "now_timestamp"),
    "flatten_dict": (".common", "flatten_dict"),
    "merge_dicts": (".common", "merge_dicts"),
    "ExperimentMetadata": (".common", "ExperimentMetadata"),
    "build_run_id": (".common", "build_run_id"),
    # io.py
    "ExperimentPaths": (".io", "ExperimentPaths"),
    "atomic_write_text": (".io", "atomic_write_text"),
    "atomic_write_bytes": (".io", "atomic_write_bytes"),
    "read_json": (".io", "read_json"),
    "write_json": (".io", "write_json"),
    "read_yaml": (".io", "read_yaml"),
    "write_yaml": (".io", "write_yaml"),
    "read_table": (".io", "read_table"),
    "write_table": (".io", "write_table"),
    # sweep.py
    "grid": (".sweep", "grid"),
    "random_search": (".sweep", "random_search"),
    "run_sweep": (".sweep", "run_sweep"),
    "SweepResult": (".sweep", "SweepResult"),
    # plotting.py (may rely on optional deps; still lazy)
    "set_plot_style": (".plotting", "set_plot_style"),
    "plot_metric_curves": (".plotting", "plot_metric_curves"),
    "plot_aggregate_summary": (".plotting", "plot_aggregate_summary"),
}
__all__ = sorted(_EXPORTS.keys())
def __getattr__(name: str):
    """Lazily resolve public attributes.

    This function is invoked when ``experiments.<name>`` is accessed and
    ``name`` is not found in the module globals. It imports the providing
    submodule on demand and returns the requested attribute.
    """
    spec = _EXPORTS.get(name)
    if spec is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = spec
    module = import_module(module_name, package=__name__)
    try:
        value = getattr(module, attr_name)
    except AttributeError as e:
        # Surface a clearer message while preserving the original exception.
        raise AttributeError(
            f"Failed to import {attr_name!r} from {module.__name__!r}"
        ) from e
    globals()[name] = value  # Cache for subsequent lookups.
    return value


def __dir__():
    return sorted(set(globals().keys()) | set(__all__))
