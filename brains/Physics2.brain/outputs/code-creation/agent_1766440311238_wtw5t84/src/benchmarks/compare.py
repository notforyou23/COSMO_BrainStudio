"""Centralized comparison utilities for benchmark outputs.

Supports absolute/relative tolerances, per-field overrides, NaN/Inf handling,
structured results, and mismatch reporting suitable for CI logs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

import math

try:  # optional
    import numpy as _np  # type: ignore
except Exception:  # pragma: no cover
    _np = None
Number = Union[int, float]

@dataclass(frozen=True)
class CompareSpec:
    atol: float = 0.0
    rtol: float = 0.0
    nan_equal: bool = True
    inf_equal: bool = True
    per_field: Dict[str, "CompareSpec"] = field(default_factory=dict)

    def for_path(self, path: str) -> "CompareSpec":
        # Exact match on full dotted path, falling back to default spec.
        return self.per_field.get(path, self)

@dataclass(frozen=True)
class Mismatch:
    path: str
    reason: str
    a: Any = None
    b: Any = None
    details: str = ""

@dataclass(frozen=True)
class CompareResult:
    ok: bool
    mismatches: Tuple[Mismatch, ...] = ()

    def raise_on_mismatch(self, prefix: str = "Comparison failed") -> None:
        if self.ok:
            return
        lines = [prefix + ":"]
        for m in self.mismatches[:50]:
            det = f" ({m.details})" if m.details else ""
            lines.append(f"- {m.path}: {m.reason}{det}; a={_short(m.a)} b={_short(m.b)}")
        if len(self.mismatches) > 50:
            lines.append(f"... and {len(self.mismatches) - 50} more mismatches")
        raise AssertionError("\n".join(lines))
def compare(a: Any, b: Any, spec: Optional[CompareSpec] = None) -> CompareResult:
    """Compare two benchmark outputs and return a structured result."""
    spec = spec or CompareSpec()
    mism: List[Mismatch] = []
    _cmp(a, b, spec, path="$", mismatches=mism)
    return CompareResult(ok=not mism, mismatches=tuple(mism))


def _cmp(a: Any, b: Any, spec: CompareSpec, path: str, mismatches: List[Mismatch]) -> None:
    specp = spec.for_path(path)

    # Fast path for exact identity / both None.
    if a is b:
        return
    if a is None or b is None:
        mismatches.append(Mismatch(path, "one is None", a, b))
        return

    # Numpy array handling (if available).
    if _np is not None and isinstance(a, _np.ndarray) and isinstance(b, _np.ndarray):
        if a.shape != b.shape:
            mismatches.append(Mismatch(path, "shape mismatch", a.shape, b.shape))
            return
        if a.dtype != b.dtype and (a.dtype.kind in "SUO" or b.dtype.kind in "SUO"):
            mismatches.append(Mismatch(path, "dtype mismatch", str(a.dtype), str(b.dtype)))
            return
        _cmp_array(a, b, specp, path, mismatches)
        return

    # Mappings.
    if isinstance(a, dict) and isinstance(b, dict):
        ka, kb = set(a.keys()), set(b.keys())
        if ka != kb:
            missing_a, missing_b = sorted(kb - ka), sorted(ka - kb)
            mismatches.append(Mismatch(path, "key mismatch", missing_b, missing_a,
                                       details=f"missing_in_a={missing_a} missing_in_b={missing_b}"))
            return
        for k in sorted(ka, key=str):
            _cmp(a[k], b[k], spec, f"{path}.{k}", mismatches)
        return

    # Sequences (but not strings/bytes).
    if _is_seq(a) and _is_seq(b):
        if len(a) != len(b):
            mismatches.append(Mismatch(path, "length mismatch", len(a), len(b)))
            return
        for i, (xa, xb) in enumerate(zip(a, b)):
            _cmp(xa, xb, spec, f"{path}[{i}]", mismatches)
        return

    # Numbers.
    if _is_number(a) and _is_number(b):
        if not _close(float(a), float(b), specp):
            mismatches.append(Mismatch(path, "number mismatch", a, b,
                                       details=f"atol={specp.atol} rtol={specp.rtol}"))
        return

    # Fallback equality with type guard.
    if type(a) != type(b):
        mismatches.append(Mismatch(path, "type mismatch", type(a).__name__, type(b).__name__))
        return
    if a != b:
        mismatches.append(Mismatch(path, "value mismatch", a, b))
def _cmp_array(a: Any, b: Any, spec: CompareSpec, path: str, mismatches: List[Mismatch]) -> None:
    # Object/string arrays: compare elementwise via Python recursion.
    if a.dtype.kind in "OSU" or b.dtype.kind in "OSU":
        a_list, b_list = a.tolist(), b.tolist()
        _cmp(a_list, b_list, spec, path, mismatches)
        return
    af, bf = a.astype(float, copy=False), b.astype(float, copy=False)
    # Compute mask of mismatching entries.
    if spec.nan_equal:
        nanmask = _np.isnan(af) & _np.isnan(bf)
    else:
        nanmask = _np.zeros_like(af, dtype=bool)
    if spec.inf_equal:
        infmask = _np.isinf(af) & _np.isinf(bf) & (_np.sign(af) == _np.sign(bf))
    else:
        infmask = _np.zeros_like(af, dtype=bool)

    finite = ~(nanmask | infmask | _np.isnan(af) | _np.isnan(bf) | _np.isinf(af) | _np.isinf(bf))
    diff = _np.abs(af - bf)
    tol = spec.atol + spec.rtol * _np.abs(bf)
    ok = nanmask | infmask | (finite & (diff <= tol))
    if bool(ok.all()):
        return
    # Report up to 10 mismatching indices with diffs.
    bad = _np.argwhere(~ok)
    for idx in bad[:10]:
        idx_t = tuple(int(x) for x in idx)
        va, vb = a[idx_t].item(), b[idx_t].item()
        da = float(af[idx_t] - bf[idx_t]) if finite[idx_t] else float("nan")
        mismatches.append(Mismatch(f"{path}{list(idx_t)}", "array element mismatch", va, vb,
                                   details=f"diff={da} atol={spec.atol} rtol={spec.rtol}"))
    if bad.shape[0] > 10:
        mismatches.append(Mismatch(path, "array has more mismatches", int(bad.shape[0]), "",
                                   details="reported first 10"))
def _close(a: float, b: float, spec: CompareSpec) -> bool:
    if math.isnan(a) or math.isnan(b):
        return spec.nan_equal and math.isnan(a) and math.isnan(b)
    if math.isinf(a) or math.isinf(b):
        return spec.inf_equal and (a == b)
    return abs(a - b) <= (spec.atol + spec.rtol * abs(b))


def _is_seq(x: Any) -> bool:
    return isinstance(x, (list, tuple)) and not isinstance(x, (str, bytes, bytearray))


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _short(x: Any, n: int = 200) -> str:
    s = repr(x)
    return s if len(s) <= n else s[: n - 3] + "..."
