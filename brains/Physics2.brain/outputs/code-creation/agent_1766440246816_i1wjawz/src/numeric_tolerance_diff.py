"""Numeric-tolerance diff for expected-vs-actual JSON-like structures.

Supports absolute/relative tolerances, per-path overrides (fnmatch), NaN/inf
handling, and produces a deterministic structured diff report.
"""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from typing import Any, Dict, Iterable, List, Optional, Tuple
import math
@dataclass(frozen=True)
class Tolerance:
    abs: float = 0.0
    rel: float = 0.0

    def threshold(self, expected_mag: float) -> float:
        return max(float(self.abs), float(self.rel) * float(expected_mag))
def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)

def _is_nan(x: Any) -> bool:
    return isinstance(x, float) and math.isnan(x)

def _is_inf(x: Any) -> bool:
    return isinstance(x, float) and math.isinf(x)

def _path_join(base: str, key: Any) -> str:
    if isinstance(key, int):
        return f"{base}[{key}]"
    if base == "$":
        return f"$.{key}"
    return f"{base}.{key}"

def _resolve_tol(path: str, default: Tolerance, overrides: Optional[Dict[str, Tolerance]]) -> Tolerance:
    if not overrides:
        return default
    best_pat, best = None, None
    for pat, tol in overrides.items():
        if fnmatch(path, pat) and (best_pat is None or len(pat) > len(best_pat)):
            best_pat, best = pat, tol
    return best if best is not None else default
def diff_json(
    expected: Any,
    actual: Any,
    *,
    abs_tol: float = 0.0,
    rel_tol: float = 0.0,
    path_tolerances: Optional[Dict[str, Tolerance]] = None,
    allow_nan_equal: bool = True,
    allow_inf_equal: bool = True,
) -> Dict[str, Any]:
    """Return a structured diff report for JSON-like objects."""
    default_tol = Tolerance(abs=abs_tol, rel=rel_tol)
    diffs: List[Dict[str, Any]] = []

    def add(kind: str, path: str, e: Any, a: Any, msg: str, **extra: Any) -> None:
        d = {"kind": kind, "path": path, "expected": e, "actual": a, "message": msg}
        d.update(extra)
        diffs.append(d)

    def cmp(e: Any, a: Any, path: str) -> None:
        # Numbers (incl. NaN/inf)
        if _is_number(e) and _is_number(a):
            if _is_nan(e) or _is_nan(a):
                if allow_nan_equal and _is_nan(e) and _is_nan(a):
                    return
                add("nan_mismatch", path, e, a, "NaN mismatch")
                return
            if _is_inf(e) or _is_inf(a):
                if allow_inf_equal and _is_inf(e) and _is_inf(a) and (math.copysign(1.0, e) == math.copysign(1.0, a)):
                    return
                add("inf_mismatch", path, e, a, "Infinity mismatch")
                return
            tol = _resolve_tol(path, default_tol, path_tolerances)
            err_abs = abs(float(e) - float(a))
            denom = max(abs(float(e)), 1e-300)
            err_rel = err_abs / denom
            thr = tol.threshold(abs(float(e)))
            ok = err_abs <= thr or err_rel <= float(tol.rel)
            if not ok:
                add(
                    "number_mismatch",
                    path,
                    e,
                    a,
                    "Numeric difference exceeds tolerance",
                    abs_err=err_abs,
                    rel_err=err_rel,
                    tol_abs=tol.abs,
                    tol_rel=tol.rel,
                    threshold=thr,
                )
            return

        # Dicts
        if isinstance(e, dict) and isinstance(a, dict):
            e_keys, a_keys = set(e.keys()), set(a.keys())
            missing, extra = sorted(e_keys - a_keys), sorted(a_keys - e_keys)
            for k in missing:
                add("missing_key", _path_join(path, k), e.get(k), None, "Key missing in actual")
            for k in extra:
                add("extra_key", _path_join(path, k), None, a.get(k), "Unexpected key in actual")
            for k in sorted(e_keys & a_keys):
                cmp(e[k], a[k], _path_join(path, k))
            return

        # Lists
        if isinstance(e, list) and isinstance(a, list):
            if len(e) != len(a):
                add("length_mismatch", path, len(e), len(a), "List length differs")
            for i, (ee, aa) in enumerate(zip(e, a)):
                cmp(ee, aa, _path_join(path, i))
            return

        # Fallback: strict equality
        if e != a:
            add("value_mismatch", path, e, a, "Values differ")

    cmp(expected, actual, "$")

    kinds: Dict[str, int] = {}
    for d in diffs:
        kinds[d["kind"]] = kinds.get(d["kind"], 0) + 1
    return {
        "ok": len(diffs) == 0,
        "diff_count": len(diffs),
        "diffs": diffs,
        "summary": {"by_kind": kinds},
        "settings": {
            "abs_tol": abs_tol,
            "rel_tol": rel_tol,
            "path_tolerances": {k: {"abs": v.abs, "rel": v.rel} for k, v in (path_tolerances or {}).items()},
            "allow_nan_equal": allow_nan_equal,
            "allow_inf_equal": allow_inf_equal,
        },
    }
def assert_json_close(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    """Convenience wrapper: raises AssertionError if diff_json is not ok."""
    report = diff_json(*args, **kwargs)
    if not report["ok"]:
        first = report["diffs"][0]
        raise AssertionError(f"JSON mismatch at {first['path']}: {first['message']}")
    return report
