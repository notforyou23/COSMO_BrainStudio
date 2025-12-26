"""Tolerant JSON comparison utilities.

This module provides a small, dependency-free recursive comparator that treats
numbers as "close" under (atol + rtol*|expected|) while comparing other JSON
types strictly.

It is used by both the benchmark reproduction code and pytest to validate that
produced JSON matches an expected artifact within numeric tolerances.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List, Sequence, Tuple
import math
@dataclass(frozen=True)
class JsonDiff:
    """A single mismatch between two JSON-like structures."""

    path: str
    expected: Any
    actual: Any
    message: str

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.path}: {self.message} (expected={self.expected!r}, actual={self.actual!r})"
def _is_number(x: Any) -> bool:
    # bool is a subclass of int; treat it separately to keep JSON semantics.
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _format_path(parent: str, token: str) -> str:
    if not parent:
        return token
    if token.startswith("["):
        return parent + token
    return parent + "." + token
def _numbers_close(actual: float, expected: float, *, rtol: float, atol: float) -> bool:
    # Mirrors numpy.isclose semantics for finite values.
    if math.isnan(expected) and math.isnan(actual):
        return True
    if math.isinf(expected) or math.isinf(actual):
        return expected == actual
    return abs(actual - expected) <= (atol + rtol * abs(expected))
def diff_json(
    actual: Any,
    expected: Any,
    *,
    rtol: float = 1e-7,
    atol: float = 1e-9,
    _path: str = "",
    _diffs: List[JsonDiff] | None = None,
    _max_diffs: int = 50,
) -> List[JsonDiff]:
    """Return a list of differences between two JSON-like structures.

    Args:
        actual: Produced value (JSON-compatible Python types).
        expected: Expected value (JSON-compatible Python types).
        rtol, atol: Numeric tolerances applied when both values are numbers.
        _max_diffs: Internal guard to keep error messages bounded.
    """
    diffs: List[JsonDiff] = [] if _diffs is None else _diffs
    if len(diffs) >= _max_diffs:
        return diffs

    # Numbers: compare with tolerance (int/float interchangeably).
    if _is_number(actual) and _is_number(expected):
        a = float(actual)
        e = float(expected)
        if not _numbers_close(a, e, rtol=rtol, atol=atol):
            diffs.append(
                JsonDiff(
                    path=_path or "$",
                    expected=expected,
                    actual=actual,
                    message=f"numbers differ (rtol={rtol}, atol={atol})",
                )
            )
        return diffs

    # Primitive JSON types: strict equality.
    if isinstance(expected, (str, bool)) or expected is None:
        if actual != expected:
            diffs.append(JsonDiff(path=_path or "$", expected=expected, actual=actual, message="values differ"))
        return diffs

    # Sequences.
    if isinstance(expected, (list, tuple)):
        if not isinstance(actual, (list, tuple)):
            diffs.append(JsonDiff(path=_path or "$", expected=expected, actual=actual, message="type differs"))
            return diffs
        if len(actual) != len(expected):
            diffs.append(
                JsonDiff(
                    path=_path or "$",
                    expected=len(expected),
                    actual=len(actual),
                    message="sequence length differs",
                )
            )
            # Still compare overlapping prefix for better diagnostics.
        for i, (a_item, e_item) in enumerate(zip(actual, expected)):
            diff_json(
                a_item,
                e_item,
                rtol=rtol,
                atol=atol,
                _path=_format_path(_path or "$", f"[{i}]"),
                _diffs=diffs,
                _max_diffs=_max_diffs,
            )
            if len(diffs) >= _max_diffs:
                break
        return diffs

    # Mappings.
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            diffs.append(JsonDiff(path=_path or "$", expected=expected, actual=actual, message="type differs"))
            return diffs
        exp_keys = set(expected.keys())
        act_keys = set(actual.keys())
        missing = sorted(exp_keys - act_keys)
        extra = sorted(act_keys - exp_keys)
        for k in missing:
            diffs.append(
                JsonDiff(
                    path=_format_path(_path or "$", str(k)),
                    expected=expected.get(k),
                    actual=None,
                    message="missing key",
                )
            )
            if len(diffs) >= _max_diffs:
                return diffs
        for k in extra:
            diffs.append(
                JsonDiff(
                    path=_format_path(_path or "$", str(k)),
                    expected=None,
                    actual=actual.get(k),
                    message="unexpected key",
                )
            )
            if len(diffs) >= _max_diffs:
                return diffs
        for k in sorted(exp_keys & act_keys, key=lambda x: str(x)):
            diff_json(
                actual[k],
                expected[k],
                rtol=rtol,
                atol=atol,
                _path=_format_path(_path or "$", str(k)),
                _diffs=diffs,
                _max_diffs=_max_diffs,
            )
            if len(diffs) >= _max_diffs:
                break
        return diffs

    # Fallback: unknown types -> strict equality (still useful for pytest).
    if actual != expected:
        diffs.append(JsonDiff(path=_path or "$", expected=expected, actual=actual, message="values differ"))
    return diffs
def assert_json_close(
    actual: Any,
    expected: Any,
    *,
    rtol: float = 1e-7,
    atol: float = 1e-9,
    max_diffs: int = 20,
) -> None:
    """Assert that two JSON-like objects match within tolerances.

    Raises AssertionError with a readable diff summary on mismatch.
    """
    diffs = diff_json(actual, expected, rtol=rtol, atol=atol, _max_diffs=max_diffs)
    if not diffs:
        return
    lines = [f"JSON mismatch: {len(diffs)} difference(s) (showing up to {max_diffs})"]
    for d in diffs:
        lines.append(str(d))
    raise AssertionError("\n".join(lines))
