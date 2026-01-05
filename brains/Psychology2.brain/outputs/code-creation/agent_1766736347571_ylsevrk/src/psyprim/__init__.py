"""psyprim: standardized workflows + lightweight tooling for primary-source scholarship.

This package provides a CLI and schemas for generating empirically grounded
validation/adoption roadmaps for standardized workflows in psychology.
"""

from __future__ import annotations
from importlib import metadata as _metadata
def _get_version() -> str:
    """Return installed distribution version; fall back to a development marker."""
    try:
        return _metadata.version("psyprim")
    except _metadata.PackageNotFoundError:
        return "0.0.0+dev"
__version__ = _get_version()
# Optional convenience imports (kept soft to allow partial installs during development).
try:
    from .schemas import (  # type: ignore
        RoadmapSpec,
        ExperimentSpec,
        MetricSpec,
        SamplingFrameSpec,
        DataCollectionSpec,
        AnalysisPlanSpec,
        export_json_schema,
    )
except Exception:  # pragma: no cover
    RoadmapSpec = ExperimentSpec = MetricSpec = SamplingFrameSpec = None  # type: ignore
    DataCollectionSpec = AnalysisPlanSpec = None  # type: ignore
    export_json_schema = None  # type: ignore
__all__ = [
    "__version__",
    "RoadmapSpec",
    "ExperimentSpec",
    "MetricSpec",
    "SamplingFrameSpec",
    "DataCollectionSpec",
    "AnalysisPlanSpec",
    "export_json_schema",
]
