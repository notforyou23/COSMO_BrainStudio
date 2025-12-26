"""Benchmark result comparison with deterministic canonicalization.

This module is shared by the benchmark runner/tests to ensure comparisons are
stable across runs and environments. It provides:

- canonical_json_bytes(obj): deterministic JSON bytes (sorted keys, stable float repr)
- compare_results(a, b, tolerance=None): structural compare with optional numeric tolerance
- compare_files(path_a, path_b, tolerance=None): convenience for JSON files
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, Tuple, Union
import json
import math
import sys
@dataclass(frozen=True)
class CompareMismatch(Exception):
    path: Tuple[Union[str, int], ...]
    message: str

    def __str__(self) -> str:
        p = "".join(f"[{k!r}]" if isinstance(k, str) else f"[{k}]" for k in self.path)
        return f"Mismatch at {p or '<root>'}: {self.message}"
def _float_token(x: float) -> str:
    # Stable, round-trippable formatting policy.
    if math.isnan(x):
        return "NaN"
    if math.isinf(x):
        return "Infinity" if x > 0 else "-Infinity"
    # repr() is deterministic in modern Python and round-trippable for floats.
    return repr(float(x))


def _normalize(obj: Any) -> Any:
    """Normalize to a JSON-safe, canonical structure.

    - dict keys are coerced to str and sorted
    - tuples/sets become lists
    - floats become tagged strings to enforce formatting policy
    """
    if obj is None or isinstance(obj, (bool, str)):
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, float):
        return {"__float__": _float_token(obj)}
    if isinstance(obj, Mapping):
        items = ((str(k), _normalize(v)) for k, v in obj.items())
        return {k: v for k, v in sorted(items, key=lambda kv: kv[0])}
    if isinstance(obj, (list, tuple, set)):
        return [_normalize(v) for v in obj]
    # Fallback: attempt to JSON-encode via string conversion.
    return str(obj)
def canonical_json_bytes(obj: Any) -> bytes:
    """Deterministically serialize an object to canonical JSON bytes."""
    norm = _normalize(obj)
    txt = json.dumps(norm, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return (txt + "\n").encode("utf-8")


def load_json(path: Union[str, Path]) -> Any:
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)
def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _compare(a: Any, b: Any, tolerance: float | None, path: Tuple[Union[str, int], ...]) -> None:
    # Handle numeric tolerance first (only for finite numbers).
    if tolerance is not None and _is_number(a) and _is_number(b):
        af, bf = float(a), float(b)
        if math.isnan(af) and math.isnan(bf):
            return
        if math.isinf(af) or math.isinf(bf):
            if af == bf:
                return
            raise CompareMismatch(path, f"{af!r} != {bf!r}")
        if abs(af - bf) <= float(tolerance):
            return
        raise CompareMismatch(path, f"{af!r} != {bf!r} (tolerance={tolerance})")

    # Canonical float tokens compare exactly when no tolerance provided.
    if isinstance(a, float) or isinstance(b, float):
        if isinstance(a, float) and isinstance(b, float):
            if _float_token(a) == _float_token(b):
                return
        raise CompareMismatch(path, f"{a!r} != {b!r}")

    if type(a) != type(b):
        raise CompareMismatch(path, f"type {type(a).__name__} != {type(b).__name__}")

    if isinstance(a, Mapping):
        ak, bk = set(a.keys()), set(b.keys())
        if ak != bk:
            missing = sorted(ak - bk)
            extra = sorted(bk - ak)
            raise CompareMismatch(path, f"keys differ missing={missing} extra={extra}")
        for k in sorted(a.keys(), key=lambda x: str(x)):
            _compare(a[k], b[k], tolerance, path + (str(k),))
        return

    if isinstance(a, Sequence) and not isinstance(a, (str, bytes, bytearray)):
        if len(a) != len(b):
            raise CompareMismatch(path, f"len {len(a)} != {len(b)}")
        for i, (av, bv) in enumerate(zip(a, b)):
            _compare(av, bv, tolerance, path + (i,))
        return

    if a != b:
        raise CompareMismatch(path, f"{a!r} != {b!r}")
def compare_results(a: Any, b: Any, tolerance: float | None = None) -> None:
    """Raise CompareMismatch if results differ.

    If tolerance is None, comparison is exact (and should match canonical JSON bytes).
    If tolerance is set, numeric leaves are compared within absolute tolerance.
    """
    _compare(a, b, tolerance, ())


def compare_files(path_a: Union[str, Path], path_b: Union[str, Path], tolerance: float | None = None) -> None:
    a = load_json(path_a)
    b = load_json(path_b)
    compare_results(a, b, tolerance=tolerance)
def _main(argv: list[str]) -> int:
    if len(argv) < 3 or len(argv) > 4:
        print("Usage: python -m benchmark_compare <a.json> <b.json> [tolerance]", file=sys.stderr)
        return 2
    tol = float(argv[3]) if len(argv) == 4 else None
    try:
        compare_files(argv[1], argv[2], tolerance=tol)
    except CompareMismatch as e:
        print(str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_main(sys.argv))
