"""Competitive landscape deliverables package.

Public API focuses on building two outputs:
- competitive_map.xlsx (or .csv fallback)
- competitive_summary.md

The underlying implementation lives in src/competitive_landscape/builder.py, but this
module provides stable import names and safe lazy imports for CLI/script usage.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence, Union

__all__ = [
    "__version__",
    "build_deliverables",
    "build_competitive_landscape",
    "load_competitors",
    "CompetitiveRecord",
]

__version__ = "0.1.0"


def _lazy_import_builder():
    try:
        from . import builder as _builder  # type: ignore
    except Exception as e:  # pragma: no cover
        raise ImportError(
            "competitive_landscape.builder is not available yet; "
            "ensure src/competitive_landscape/builder.py exists and is importable."
        ) from e
    return _builder


def _lazy_import_schemas():
    try:
        from . import schemas as _schemas  # type: ignore
    except Exception as e:  # pragma: no cover
        raise ImportError(
            "competitive_landscape.schemas is not available yet; "
            "ensure src/competitive_landscape/schemas.py exists and is importable."
        ) from e
    return _schemas


def load_competitors(
    source: Optional[Union[str, "PathLike[str]"]] = None,
    *,
    overrides: Optional[Sequence[dict]] = None,
) -> list:
    """Load competitor records from a CSV/JSON source, optionally applying overrides.

    Delegates to builder.load_competitors if present; otherwise raises ImportError.
    """
    b = _lazy_import_builder()
    if not hasattr(b, "load_competitors"):
        raise AttributeError("builder.load_competitors is not defined.")
    return b.load_competitors(source=source, overrides=overrides)


def build_deliverables(
    *,
    competitors_source: Optional[Union[str, "PathLike[str]"]] = None,
    outputs_dir: Optional[Union[str, "PathLike[str]"]] = None,
    overrides: Optional[Sequence[dict]] = None,
    prefer_excel: bool = True,
    **kwargs: Any,
) -> dict:
    """Build competitive_map + competitive_summary outputs.

    Returns a dict with output paths/metadata as provided by builder.build_deliverables.
    """
    b = _lazy_import_builder()
    if not hasattr(b, "build_deliverables"):
        raise AttributeError("builder.build_deliverables is not defined.")
    return b.build_deliverables(
        competitors_source=competitors_source,
        outputs_dir=outputs_dir,
        overrides=overrides,
        prefer_excel=prefer_excel,
        **kwargs,
    )


def build_competitive_landscape(
    *args: Any, **kwargs: Any
) -> dict:
    """Alias for build_deliverables (legacy-friendly name)."""
    return build_deliverables(*args, **kwargs)


try:
    CompetitiveRecord = _lazy_import_schemas().CompetitiveRecord  # type: ignore
except Exception:  # pragma: no cover
    CompetitiveRecord = None  # type: ignore
