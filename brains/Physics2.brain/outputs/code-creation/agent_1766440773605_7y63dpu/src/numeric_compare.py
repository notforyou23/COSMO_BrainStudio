"""numeric_compare

Small numeric comparison helpers plus a tiny CLI.

Typical use:
    python -m numeric_compare --expected 1.0 --actual 1.0001 --rtol 1e-3
"""

from __future__ import annotations

from dataclasses import dataclass
import argparse
import json
import math
import os
from pathlib import Path
from typing import Any, Iterable, Sequence, Tuple, Union

Number = Union[int, float]
JSONLike = Union[Number, Sequence[Any]]


@dataclass(frozen=True)
class CompareResult:
    ok: bool
    max_abs_err: float
    max_rel_err: float
    message: str = ""


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _as_float(x: Any) -> float:
    try:
        return float(x)
    except Exception as e:  # pragma: no cover
        raise TypeError(f"Not a number: {x!r}") from e
def _scalar_ok(a: float, b: float, *, rtol: float, atol: float) -> Tuple[bool, float, float]:
    if not (math.isfinite(a) and math.isfinite(b)):
        return (a == b), float("nan"), float("nan")
    abs_err = abs(a - b)
    denom = max(abs(a), abs(b), 1e-300)
    rel_err = abs_err / denom
    ok = abs_err <= (atol + rtol * max(abs(a), abs(b)))
    return ok, abs_err, rel_err


def compare_numeric(expected: Any, actual: Any, *, rtol: float = 1e-6, atol: float = 0.0) -> CompareResult:
    """Compare numbers or nested JSON-like sequences.

    Returns the maximum absolute/relative error over all scalar elements.
    """
    if _is_number(expected) and _is_number(actual):
        ok, aerr, rerr = _scalar_ok(_as_float(expected), _as_float(actual), rtol=rtol, atol=atol)
        msg = "OK" if ok else f"FAIL abs_err={aerr:g} rel_err={rerr:g}"
        return CompareResult(ok=ok, max_abs_err=aerr, max_rel_err=rerr, message=msg)

    if isinstance(expected, (list, tuple)) and isinstance(actual, (list, tuple)):
        if len(expected) != len(actual):
            return CompareResult(False, float("inf"), float("inf"), f"Length mismatch: {len(expected)} != {len(actual)}")
        max_abs = 0.0
        max_rel = 0.0
        for e, a in zip(expected, actual):
            r = compare_numeric(e, a, rtol=rtol, atol=atol)
            if not r.ok:
                return CompareResult(False, max(max_abs, r.max_abs_err), max(max_rel, r.max_rel_err), r.message)
            max_abs = max(max_abs, r.max_abs_err)
            max_rel = max(max_rel, r.max_rel_err)
        return CompareResult(True, max_abs, max_rel, "OK")

    return CompareResult(False, float("inf"), float("inf"), f"Type mismatch: {type(expected).__name__} vs {type(actual).__name__}")
def _read_text_if_path(s: str) -> str:
    p = Path(s)
    if p.exists() and p.is_file():
        return p.read_text(encoding="utf-8").strip()
    return s.strip()


def parse_value(text_or_path: str) -> JSONLike:
    """Parse a scalar number or a JSON array from a string or file path."""
    text = _read_text_if_path(text_or_path)
    # Try JSON first (handles lists, ints, floats)
    try:
        v = json.loads(text)
        if _is_number(v) or isinstance(v, (list, tuple)):
            return v
    except Exception:
        pass
    # Fallback: first token as float
    tok = text.split()[0] if text else ""
    try:
        return float(tok)
    except Exception as e:
        raise ValueError(f"Could not parse numeric value from {text_or_path!r}") from e


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="numeric_compare", description="Compare numeric values with tolerances.")
    p.add_argument("--expected", required=True, help="Expected number / JSON list, or path to a file containing it.")
    p.add_argument("--actual", required=True, help="Actual number / JSON list, or path to a file containing it.")
    p.add_argument("--rtol", type=float, default=1e-6, help="Relative tolerance (default: 1e-6).")
    p.add_argument("--atol", type=float, default=0.0, help="Absolute tolerance (default: 0.0).")
    p.add_argument("--quiet", action="store_true", help="Suppress OK output; only print failures.")
    return p


def main(argv: Iterable[str] | None = None) -> int:
    args = build_arg_parser().parse_args(list(argv) if argv is not None else None)
    expected = parse_value(args.expected)
    actual = parse_value(args.actual)
    res = compare_numeric(expected, actual, rtol=args.rtol, atol=args.atol)
    if res.ok:
        if not args.quiet:
            print(f"OK max_abs_err={res.max_abs_err:g} max_rel_err={res.max_rel_err:g}")
        return 0
    print(res.message or "FAIL")
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
