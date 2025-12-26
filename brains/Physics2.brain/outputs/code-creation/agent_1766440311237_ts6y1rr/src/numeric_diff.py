"""numeric_diff.py

Tolerance-aware recursive comparison for JSON-like structures.

Supports dict/list/tuple/scalars and numeric comparisons with absolute and
relative tolerances. Produces clear, path-addressed mismatch messages.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Sequence, Mapping
import math


_JSON_SCALARS = (str, int, float, bool, type(None))


@dataclass
class DiffResult:
    ok: bool
    mismatches: List[str]

    def __bool__(self) -> bool:  # convenience
        return self.ok


def _is_number(x: Any) -> bool:
    # bool is a subclass of int; treat separately to avoid surprises.
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _path_join(path: str, token: str) -> str:
    if not path:
        return "$" + token
    return path + token


def _format_value(x: Any) -> str:
    if isinstance(x, float):
        if math.isnan(x):
            return "NaN"
        if math.isinf(x):
            return "Infinity" if x > 0 else "-Infinity"
        # repr keeps enough precision while staying deterministic.
        return repr(x)
    return repr(x)


def _numbers_close(a: float, b: float, abs_tol: float, rel_tol: float) -> bool:
    # Handle NaN/inf explicitly.
    if math.isnan(a) or math.isnan(b):
        return math.isnan(a) and math.isnan(b)
    if math.isinf(a) or math.isinf(b):
        return a == b
    diff = abs(a - b)
    scale = max(abs(a), abs(b), 0.0)
    return diff <= max(abs_tol, rel_tol * scale)


def compare(
    actual: Any,
    expected: Any,
    *,
    abs_tol: float = 0.0,
    rel_tol: float = 0.0,
    path: str = "",
    max_mismatches: int = 50,
) -> DiffResult:
    """Compare two JSON-like structures.

    Parameters
    ----------
    actual, expected:
        Structures composed of dict/list/tuple/scalars.
    abs_tol, rel_tol:
        Numeric tolerances used when comparing ints/floats (except bool).
    path:
        Root path for reporting; by default starts at '$'.
    max_mismatches:
        Stop collecting mismatch strings after this many entries.
    """
    mismatches: List[str] = []

    def add(msg: str) -> None:
        if len(mismatches) < max_mismatches:
            mismatches.append(msg)

    def rec(a: Any, e: Any, p: str) -> None:
        if len(mismatches) >= max_mismatches:
            return

        # Numeric comparisons with tolerance
        if _is_number(a) and _is_number(e):
            af, ef = float(a), float(e)
            if not _numbers_close(af, ef, abs_tol, rel_tol):
                diff = abs(af - ef) if (not math.isnan(af) and not math.isnan(ef)) else float("nan")
                add(
                    f"{p or '$'}: numbers differ actual={_format_value(a)} expected={_format_value(e)} "
                    f"abs_diff={_format_value(diff)} abs_tol={abs_tol} rel_tol={rel_tol}"
                )
            return

        # Type mismatch fast path (but allow tuple/list interchange)
        if isinstance(a, (list, tuple)) and isinstance(e, (list, tuple)):
            a_seq: Sequence[Any] = list(a)
            e_seq: Sequence[Any] = list(e)
            if len(a_seq) != len(e_seq):
                add(f"{p or '$'}: length differs actual={len(a_seq)} expected={len(e_seq)}")
                # still compare overlapping prefix for more detail
            for i in range(min(len(a_seq), len(e_seq))):
                rec(a_seq[i], e_seq[i], _path_join(p or '$', f"[{i}]"))
            return

        if isinstance(a, Mapping) and isinstance(e, Mapping):
            a_keys = set(a.keys())
            e_keys = set(e.keys())
            missing = sorted(e_keys - a_keys)
            extra = sorted(a_keys - e_keys)
            for k in missing:
                add(f"{_path_join(p or '$', '.' + str(k))}: missing key (expected present)")
            for k in extra:
                add(f"{_path_join(p or '$', '.' + str(k))}: unexpected key (actual present)")
            for k in sorted(a_keys & e_keys, key=lambda x: str(x)):
                rec(a[k], e[k], _path_join(p or '$', '.' + str(k)))
            return

        # Scalar comparisons (including None/bool/str) and all other objects by equality
        if a != e:
            add(f"{p or '$'}: value differs actual={_format_value(a)} expected={_format_value(e)}")

    rec(actual, expected, path)
    return DiffResult(ok=(len(mismatches) == 0), mismatches=mismatches)


def diff_summary(result: DiffResult, *, max_lines: int = 20) -> str:
    """Human-readable summary string for a DiffResult."""
    if result.ok:
        return "OK"
    lines = [f"MISMATCHES: {len(result.mismatches)}"]
    for m in result.mismatches[:max_lines]:
        lines.append(m)
    if len(result.mismatches) > max_lines:
        lines.append(f"... ({len(result.mismatches) - max_lines} more)")
    return "\n".join(lines)
