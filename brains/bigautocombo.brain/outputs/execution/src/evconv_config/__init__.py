"""evconv_config package.

Public API surface for notebook use:
- Assumptions: segment defaults + merge/validation helpers
- Drive cycles: standard proxy cycles + resampling/selection helpers
- IO/modeling: optional modules re-exported when available
"""
from __future__ import annotations
from importlib import import_module

__version__ = "0.1.0"

def _optional(module: str, names: list[str]):
    """Return dict(name->obj) for importable symbols; skip missing modules/symbols."""
    try:
        m = import_module(module)
    except Exception:
        return {}
    out = {}
    for n in names:
        try:
            out[n] = getattr(m, n)
        except Exception:
            pass
    return out
_assump = _optional(
    "evconv_config.assumptions",
    [
        "SEGMENT_DEFAULTS",
        "DEFAULT_TOGGLES",
        "ASSUMPTION_SCHEMA",
        "get_segment_defaults",
        "merge_user_overrides",
        "validate_assumptions",
    ],
)
globals().update(_assump)
_cycles = _optional(
    "evconv_config.drive_cycles",
    [
        "CYCLE_PROXIES",
        "get_cycle",
        "list_cycles",
        "resample_cycle",
        "cycle_distance_km",
        "cycle_mean_speed_kph",
    ],
)
globals().update(_cycles)
_io = _optional(
    "evconv_config.io",
    [
        "load_user_inputs_csv",
        "write_results_csv",
        "load_template_csv",
    ],
)
globals().update(_io)
_model = _optional(
    "evconv_config.model",
    [
        "run_scenario",
        "run_batch",
        "compare_powertrains",
        "summarize_results",
    ],
)
globals().update(_model)
__all__ = sorted(
    {
        "__version__",
        "SEGMENT_DEFAULTS",
        "DEFAULT_TOGGLES",
        "ASSUMPTION_SCHEMA",
        "get_segment_defaults",
        "merge_user_overrides",
        "validate_assumptions",
        "CYCLE_PROXIES",
        "get_cycle",
        "list_cycles",
        "resample_cycle",
        "cycle_distance_km",
        "cycle_mean_speed_kph",
        "load_user_inputs_csv",
        "write_results_csv",
        "load_template_csv",
        "run_scenario",
        "run_batch",
        "compare_powertrains",
        "summarize_results",
    }
    & set(globals().keys())
)
