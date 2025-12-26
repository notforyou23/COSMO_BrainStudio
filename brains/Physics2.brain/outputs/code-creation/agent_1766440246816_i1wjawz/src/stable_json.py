"""Stable, reproducible JSON serialization utilities.

This module aims for byte-for-byte identical JSON output across machines and CI by:
- canonical key ordering (via sort_keys=True),
- normalized float rendering (stable formatting, -0.0 -> 0.0),
- consistent indentation and newline handling,
- basic canonicalization for common non-JSON-native Python types.
"""

from __future__ import annotations

from dataclasses import is_dataclass, asdict
import json
import math
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Sequence
def canonicalize(obj: Any) -> Any:
    """Convert common Python objects into JSON-serializable, stable structures."""
    if obj is None or isinstance(obj, (str, int, bool)):
        return obj
    if isinstance(obj, float):
        # Normalize negative zero; keep NaN/Infinity as-is (JSON module handles via allow_nan).
        if obj == 0.0:
            return 0.0
        return obj
    if isinstance(obj, (bytes, bytearray, memoryview)):
        return obj.hex()
    if isinstance(obj, Path):
        return str(obj)
    if is_dataclass(obj):
        return canonicalize(asdict(obj))
    if isinstance(obj, Mapping):
        # Ensure plain dict values; keys must be str for JSON (convert defensively).
        out: MutableMapping[str, Any] = {}
        for k, v in obj.items():
            out[str(k)] = canonicalize(v)
        return out
    if isinstance(obj, (list, tuple)):
        return [canonicalize(v) for v in obj]
    if isinstance(obj, set):
        return sorted((canonicalize(v) for v in obj), key=lambda x: json.dumps(x, sort_keys=True))
    # Common scalar-like objects (e.g., numpy scalars) expose item()
    item = getattr(obj, "item", None)
    if callable(item):
        try:
            return canonicalize(item())
        except Exception:
            pass
    # Fallback: try __dict__ if it looks like a simple record.
    d = getattr(obj, "__dict__", None)
    if isinstance(d, dict) and d:
        return canonicalize(d)
    return obj
def _float_to_str(x: float) -> str:
    """Stable float rendering for JSON (handles -0.0, NaN/inf)."""
    if math.isnan(x):
        return "NaN"
    if math.isinf(x):
        return "Infinity" if x > 0 else "-Infinity"
    if x == 0.0:
        x = 0.0  # removes negative zero
    # 17 significant digits round-trips IEEE-754 double.
    s = format(x, ".17g")
    # Ensure JSON-compliant exponent with lowercase 'e' (format already uses 'e').
    return s
class StableJSONEncoder(json.JSONEncoder):
    """JSONEncoder with stable float formatting."""

    def iterencode(self, o: Any, _one_shot: bool = False):
        # Adapted from Python's stdlib json.encoder, with custom float formatting.
        if self.check_circular:
            markers = {}
        else:
            markers = None
        _encoder = json.encoder.encode_basestring_ascii if self.ensure_ascii else json.encoder.encode_basestring

        def floatstr(
            value,
            allow_nan=self.allow_nan,
            _inf=math.inf,
            _neginf=-math.inf,
        ):
            if value != value:
                text = "NaN"
            elif value == _inf:
                text = "Infinity"
            elif value == _neginf:
                text = "-Infinity"
            else:
                text = _float_to_str(value)
            if not allow_nan and text in ("NaN", "Infinity", "-Infinity"):
                raise ValueError("Out of range float values are not JSON compliant")
            return text

        _iterencode = json.encoder._make_iterencode(
            markers,
            self.default,
            _encoder,
            self.indent,
            floatstr,
            self.key_separator,
            self.item_separator,
            self.sort_keys,
            self.skipkeys,
            _one_shot,
        )
        return _iterencode(o, 0)
def dumps(obj: Any, *, indent: int = 2, ensure_ascii: bool = False) -> str:
    """Deterministically serialize to JSON text (always ends with a single '\n')."""
    canon = canonicalize(obj)
    text = json.dumps(
        canon,
        cls=StableJSONEncoder,
        sort_keys=True,
        ensure_ascii=ensure_ascii,
        indent=indent,
        separators=(",", ": ") if indent else (",", ":"),
        allow_nan=True,
    )
    return text + "\n"


def dump(obj: Any, fp, *, indent: int = 2, ensure_ascii: bool = False) -> None:
    """Write stable JSON to a file-like object."""
    fp.write(dumps(obj, indent=indent, ensure_ascii=ensure_ascii))


def write_text(path: str | Path, obj: Any, *, indent: int = 2, ensure_ascii: bool = False) -> Path:
    """Write stable JSON to a filesystem path (UTF-8)."""
    p = Path(path)
    p.write_text(dumps(obj, indent=indent, ensure_ascii=ensure_ascii), encoding="utf-8", newline="\n")
    return p
