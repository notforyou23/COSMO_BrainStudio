"""trialplanner: Build, validate, and render multi-wave randomized trial plans.

This package exposes a small public API centered on:
- data models (schema)
- curated catalogs for plan assembly
- helper functions to validate and render plans

The public API is designed to remain stable as the internal module layout evolves.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("trialplanner")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"


def _optional_import(module: str, names: list[str]) -> dict[str, object]:
    """Import names from a module if available; otherwise return an empty dict.

    This keeps the package importable even when optional modules are created in later
    build stages or in partial installs used for documentation generation.
    """
    try:
        m = __import__(module, fromlist=names)
    except Exception:  # pragma: no cover
        return {}
    out: dict[str, object] = {}
    for n in names:
        try:
            out[n] = getattr(m, n)
        except AttributeError:
            pass
    return out
# Schema models (core plan specification)
_schema = _optional_import(
    "trialplanner.schema",
    [
        "TrialPlan",
        "Arm",
        "Wave",
        "ZPDSupport",
        "ZPDType",
        "ZPDTiming",
        "ZPDFading",
        "Measure",
        "Mediator",
        "Outcome",
        "CausalTest",
        "ValidationResult",
        "validate_plan",
        "validate_plan_or_raise",
    ],
)
globals().update(_schema)
# Catalogs (curated components to build mechanism-oriented plans)
_catalogs = _optional_import(
    "trialplanner.catalogs",
    [
        "INTERVENTION_COMPONENTS",
        "COGNITIVE_TASKS",
        "MEDIATOR_MEASURES",
        "DISTAL_OUTCOMES",
        "ZPD_EXAMPLES",
        "get_component",
        "get_task",
        "get_measure",
        "get_outcome",
        "get_zpd_example",
    ],
)
globals().update(_catalogs)
# Rendering (human-readable or structured representations)
_rendering = _optional_import(
    "trialplanner.rendering",
    [
        "render_plan_text",
        "render_plan_markdown",
        "render_plan_json",
        "to_dict",
        "to_json",
    ],
)
globals().update(_rendering)
# Public API surface (best-effort; missing symbols are simply omitted)
__all__ = ["__version__"]
for _name in (
    list(_schema.keys())
    + list(_catalogs.keys())
    + list(_rendering.keys())
):
    if _name.startswith("_"):
        continue
    __all__.append(_name)
del _name, _schema, _catalogs, _rendering
