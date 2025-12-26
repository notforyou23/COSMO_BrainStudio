"""Utilities for comparing nested JSON-like structures in tests.

Designed for pytest assertions with informative diffs and numeric tolerances.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, List, Tuple


PathStr = str
Diff = Tuple[PathStr, Any, Any, str]  # (path, actual, expected, reason)


def _is_number(x: Any) -> bool:
    # bool is a subclass of int; treat it as non-numeric for comparisons.
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _fmt_value(x: Any, maxlen: int = 200) -> str:
    s = repr(x)
    return s if len(s) <= maxlen else s[: maxlen - 3] + "..."


def _num_equal(a: float, b: float, *, atol: float, rtol: float) -> bool:
    # Handle NaN/inf in a predictable way.
    if math.isnan(a) and math.isnan(b):
        return True
    if math.isinf(a) or math.isinf(b):
        return a == b
    return math.isclose(a, b, rel_tol=rtol, abs_tol=atol)


def compare_json_like(
    actual: Any,
    expected: Any,
    *,
    atol: float = 1e-8,
    rtol: float = 1e-6,
    path: str = "",
    max_diffs: int | None = None,
) -> List[Diff]:
    """Recursively compare JSON-like structures.

    Returns a list of diffs. An empty list means equal within tolerances.
    """

    diffs: List[Diff] = []

    def add(reason: str, a: Any = actual, e: Any = expected) -> None:
        diffs.append((path or "$", a, e, reason))

    # Type-based dispatch
    if _is_number(actual) and _is_number(expected):
        if not _num_equal(float(actual), float(expected), atol=atol, rtol=rtol):
            add(f"numbers differ (atol={atol}, rtol={rtol})")
        return diffs

    if actual is None or expected is None:
        if actual is not expected:
            add("one is None")
        return diffs

    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            add(f"type mismatch: {type(actual).__name__} != dict")
            return diffs
        a_keys = set(actual.keys())
        e_keys = set(expected.keys())
        for k in sorted(e_keys - a_keys):
            diffs.append((f"{path or '$'}.{k}", None, expected[k], "missing key"))
            if max_diffs is not None and len(diffs) >= max_diffs:
                return diffs
        for k in sorted(a_keys - e_keys):
            diffs.append((f"{path or '$'}.{k}", actual[k], None, "unexpected key"))
            if max_diffs is not None and len(diffs) >= max_diffs:
                return diffs
        for k in sorted(a_keys & e_keys, key=lambda x: str(x)):
            subpath = f"{path or '$'}.{k}"
            diffs.extend(
                compare_json_like(
                    actual[k],
                    expected[k],
                    atol=atol,
                    rtol=rtol,
                    path=subpath,
                    max_diffs=None if max_diffs is None else max_diffs - len(diffs),
                )
            )
            if max_diffs is not None and len(diffs) >= max_diffs:
                return diffs
        return diffs

    if isinstance(expected, (list, tuple)):
        if not isinstance(actual, (list, tuple)):
            add(f"type mismatch: {type(actual).__name__} != list")
            return diffs
        if len(actual) != len(expected):
            add(f"length mismatch: {len(actual)} != {len(expected)}", actual, expected)
            if max_diffs is not None and len(diffs) >= max_diffs:
                return diffs
        n = min(len(actual), len(expected))
        for i in range(n):
            subpath = f"{path or '$'}[{i}]"
            diffs.extend(
                compare_json_like(
                    actual[i],
                    expected[i],
                    atol=atol,
                    rtol=rtol,
                    path=subpath,
                    max_diffs=None if max_diffs is None else max_diffs - len(diffs),
                )
            )
            if max_diffs is not None and len(diffs) >= max_diffs:
                return diffs
        return diffs

    # Fallback: strict equality (covers str, bool, etc.)
    if actual != expected:
        add("value mismatch")
    return diffs


def format_diffs(diffs: Iterable[Diff], *, max_lines: int = 30) -> str:
    """Human-friendly multiline diff for assertion errors."""
    diffs = list(diffs)
    if not diffs:
        return ""
    lines: List[str] = []
    show = diffs[:max_lines]
    for p, a, e, reason in show:
        lines.append(f"- {p}: {reason}")
        lines.append(f"    actual:   {_fmt_value(a)}")
        lines.append(f"    expected: {_fmt_value(e)}")
    if len(diffs) > len(show):
        lines.append(f"... {len(diffs) - len(show)} more differences not shown")
    return "\n".join(lines)


def assert_json_like_equal(
    actual: Any,
    expected: Any,
    *,
    atol: float = 1e-8,
    rtol: float = 1e-6,
    max_diffs: int = 50,
) -> None:
    """Assert equality with numeric tolerances; raises AssertionError with diff."""
    diffs = compare_json_like(actual, expected, atol=atol, rtol=rtol, max_diffs=max_diffs)
    if diffs:
        raise AssertionError(
            "JSON-like structures differ:\n" + format_diffs(diffs, max_lines=max_diffs)
        )
