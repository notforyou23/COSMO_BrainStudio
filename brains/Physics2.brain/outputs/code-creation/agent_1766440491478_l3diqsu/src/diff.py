"""Utilities for numeric and structured diffs with tolerances.

This module is used by benchmark tooling to decide whether an artifact matches a
golden reference within absolute/relative numeric tolerances, while still
providing a human-friendly mismatch summary.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, isnan
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union
Number = Union[int, float]

_DEFAULT_ABS_TOL = 1e-8
_DEFAULT_REL_TOL = 1e-6
_TINY = 1e-12
@dataclass
class DiffStats:
    """Aggregate diff outcome and a small sample of mismatches."""

    ok: bool = True
    mismatches: int = 0
    max_abs_err: float = 0.0
    max_rel_err: float = 0.0
    examples: List[str] = None  # filled in __post_init__

    def __post_init__(self) -> None:
        if self.examples is None:
            self.examples = []

    def add_example(self, msg: str, limit: int) -> None:
        if len(self.examples) < limit:
            self.examples.append(msg)

    def update_numeric(self, abs_err: float, rel_err: float) -> None:
        self.max_abs_err = max(self.max_abs_err, abs_err)
        self.max_rel_err = max(self.max_rel_err, rel_err)
def _is_number(x: Any) -> bool:
    # bool is an int subclass; treat it as non-numeric for diffs.
    return isinstance(x, (int, float)) and not isinstance(x, bool)
def numeric_close(
    a: Number,
    b: Number,
    *,
    abs_tol: float = _DEFAULT_ABS_TOL,
    rel_tol: float = _DEFAULT_REL_TOL,
) -> Tuple[bool, float, float]:
    """Return (ok, abs_err, rel_err) for numeric values.

    rel_err is scaled by max(|a|,|b|,tiny) to avoid division by zero.
    NaNs compare equal only to NaN; inf compares exactly by sign.
    """
    if isinstance(a, bool) or isinstance(b, bool):
        return (a == b, float(a != b), float(a != b))
    if isnan(float(a)) or isnan(float(b)):
        ok = isnan(float(a)) and isnan(float(b))
        return ok, float("inf") if not ok else 0.0, float("inf") if not ok else 0.0
    if not (isfinite(float(a)) and isfinite(float(b))):
        ok = float(a) == float(b)
        return ok, float("inf") if not ok else 0.0, float("inf") if not ok else 0.0

    abs_err = abs(float(a) - float(b))
    scale = max(abs(float(a)), abs(float(b)), _TINY)
    rel_err = abs_err / scale
    ok = abs_err <= abs_tol or rel_err <= rel_tol
    return ok, abs_err, rel_err
def diff(
    expected: Any,
    actual: Any,
    *,
    abs_tol: float = _DEFAULT_ABS_TOL,
    rel_tol: float = _DEFAULT_REL_TOL,
    max_examples: int = 20,
) -> DiffStats:
    """Diff two JSON-like structures with numeric tolerances."""
    stats = DiffStats()
    _diff_into(
        expected,
        actual,
        path="$",
        stats=stats,
        abs_tol=abs_tol,
        rel_tol=rel_tol,
        max_examples=max_examples,
    )
    stats.ok = stats.mismatches == 0
    return stats
def _diff_into(
    expected: Any,
    actual: Any,
    *,
    path: str,
    stats: DiffStats,
    abs_tol: float,
    rel_tol: float,
    max_examples: int,
) -> None:
    if expected is actual:
        return

    if _is_number(expected) and _is_number(actual):
        ok, abs_err, rel_err = numeric_close(
            expected, actual, abs_tol=abs_tol, rel_tol=rel_tol
        )
        stats.update_numeric(abs_err, rel_err)
        if not ok:
            stats.mismatches += 1
            stats.add_example(
                f"{path}: expected {expected!r} got {actual!r} (abs={abs_err:.3g}, rel={rel_err:.3g})",
                max_examples,
            )
        return

    if type(expected) != type(actual):
        stats.mismatches += 1
        stats.add_example(
            f"{path}: type mismatch expected {type(expected).__name__} got {type(actual).__name__}",
            max_examples,
        )
        return

    if isinstance(expected, Mapping):
        exp_keys = set(expected.keys())
        act_keys = set(actual.keys())
        missing = sorted(exp_keys - act_keys)
        extra = sorted(act_keys - exp_keys)
        for k in missing:
            stats.mismatches += 1
            stats.add_example(f"{path}.{k}: missing key", max_examples)
        for k in extra:
            stats.mismatches += 1
            stats.add_example(f"{path}.{k}: unexpected key", max_examples)
        for k in sorted(exp_keys & act_keys, key=lambda x: str(x)):
            _diff_into(
                expected[k],
                actual[k],
                path=f"{path}.{k}",
                stats=stats,
                abs_tol=abs_tol,
                rel_tol=rel_tol,
                max_examples=max_examples,
            )
        return

    if isinstance(expected, (list, tuple)):
        if len(expected) != len(actual):
            stats.mismatches += 1
            stats.add_example(
                f"{path}: length mismatch expected {len(expected)} got {len(actual)}",
                max_examples,
            )
        for i, (e, a) in enumerate(zip(expected, actual)):
            _diff_into(
                e,
                a,
                path=f"{path}[{i}]",
                stats=stats,
                abs_tol=abs_tol,
                rel_tol=rel_tol,
                max_examples=max_examples,
            )
        return

    # Fallback: strict equality for scalars (str/bool/None, etc.)
    if expected != actual:
        stats.mismatches += 1
        stats.add_example(f"{path}: expected {expected!r} got {actual!r}", max_examples)
def format_summary(stats: DiffStats) -> str:
    """Human-readable one-paragraph summary."""
    if stats.ok:
        return (
            f"OK (mismatches=0, max_abs_err={stats.max_abs_err:.3g}, "
            f"max_rel_err={stats.max_rel_err:.3g})"
        )
    head = (
        f"FAIL (mismatches={stats.mismatches}, max_abs_err={stats.max_abs_err:.3g}, "
        f"max_rel_err={stats.max_rel_err:.3g})"
    )
    if not stats.examples:
        return head
    lines = "\n".join(f"- {e}" for e in stats.examples)
    return head + "\n" + lines
def diff_ok(
    expected: Any,
    actual: Any,
    *,
    abs_tol: float = _DEFAULT_ABS_TOL,
    rel_tol: float = _DEFAULT_REL_TOL,
) -> bool:
    """Convenience boolean check."""
    return diff(expected, actual, abs_tol=abs_tol, rel_tol=rel_tol).ok
