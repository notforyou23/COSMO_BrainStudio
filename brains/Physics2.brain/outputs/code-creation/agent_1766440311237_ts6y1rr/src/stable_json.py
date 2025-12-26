"""Stable, deterministic JSON serialization utilities.

This module is used by benchmarks to produce repeatable artifacts and to
serialize results in a canonical form (stable key ordering, float
normalization, consistent formatting).
"""

from __future__ import annotations

import json
import math
from typing import Any, Mapping, Sequence, Union, IO, Optional


JsonLike = Union[None, bool, int, float, str, Sequence["JsonLike"], Mapping[str, "JsonLike"]]
def _normalize_float(x: float, precision: int) -> float:
    """Normalize floats for stable cross-run JSON output.

    - Rounds to a configurable significant decimal precision.
    - Converts -0.0 to 0.0.
    - Disallows NaN/Infinity (JSON-incompatible in strict mode).
    """
    if not math.isfinite(x):
        raise ValueError(f"Non-finite float is not JSON compatible: {x!r}")
    if precision is None:
        y = float(x)
    else:
        y = round(float(x), int(precision))
    # Avoid negative zero which can appear after rounding.
    return 0.0 if y == 0.0 else y
def normalize(obj: Any, *, float_precision: int = 15) -> Any:
    """Recursively normalize a JSON-like structure for canonical serialization."""
    if obj is None or isinstance(obj, (bool, int, str)):
        return obj
    if isinstance(obj, float):
        return _normalize_float(obj, float_precision)
    if isinstance(obj, (list, tuple)):
        return [normalize(v, float_precision=float_precision) for v in obj]
    if isinstance(obj, dict):
        # JSON object keys must be strings; coerce for stability.
        return {
            str(k): normalize(v, float_precision=float_precision)
            for k, v in obj.items()
        }
    # Allow callers to pass objects implementing __json__ or similar patterns.
    to_json = getattr(obj, "__json__", None)
    if callable(to_json):
        return normalize(to_json(), float_precision=float_precision)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
def dumps(
    obj: Any,
    *,
    float_precision: int = 15,
    indent: Optional[int] = None,
    sort_keys: bool = True,
) -> str:
    """Serialize to a stable JSON string.

    Defaults:
      - sort_keys=True for canonical key ordering
      - ensure_ascii=False to preserve unicode deterministically
      - compact separators when indent is None
      - allow_nan=False for strict JSON
    """
    norm = normalize(obj, float_precision=float_precision)
    if indent is None:
        separators = (",", ":")
    else:
        separators = (",", ": ")
    return json.dumps(
        norm,
        sort_keys=sort_keys,
        indent=indent,
        ensure_ascii=False,
        allow_nan=False,
        separators=separators,
    )
def dump(
    obj: Any,
    fp: IO[str],
    *,
    float_precision: int = 15,
    indent: Optional[int] = None,
    sort_keys: bool = True,
) -> None:
    """Write stable JSON to a file-like object."""
    fp.write(
        dumps(
            obj,
            float_precision=float_precision,
            indent=indent,
            sort_keys=sort_keys,
        )
    )
def loads(s: str) -> Any:
    """Parse JSON (thin wrapper around json.loads)."""
    return json.loads(s)
def canonicalize(obj: Any, *, float_precision: int = 15) -> Any:
    """Return a normalized JSON-like structure suitable for stable comparison."""
    return normalize(obj, float_precision=float_precision)
