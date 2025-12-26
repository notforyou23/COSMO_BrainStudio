"""Benchmark comparison entrypoint with deterministic numeric tolerances.

This module provides a small JSON-like structural comparator that supports:
- Per-observable absolute/relative tolerances (by exact JSONPath-like key, last key, or '*')
- Deterministic dict key traversal and list alignment
- Seeded randomness only for tie-breaking when list items share the same identifier
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
import argparse
import json
import math
import random
@dataclass(frozen=True)
class Tolerance:
    atol: float = 0.0
    rtol: float = 0.0

    @staticmethod
    def coerce(obj: Any) -> "Tolerance":
        if obj is None:
            return Tolerance()
        if isinstance(obj, Tolerance):
            return obj
        if isinstance(obj, (int, float)) and not isinstance(obj, bool):
            return Tolerance(float(obj), 0.0)
        if isinstance(obj, Mapping):
            return Tolerance(float(obj.get("atol", 0.0)), float(obj.get("rtol", 0.0)))
        if isinstance(obj, (tuple, list)) and len(obj) >= 2:
            return Tolerance(float(obj[0]), float(obj[1]))
        raise TypeError(f"Unsupported tolerance spec: {type(obj)!r}")
def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _path_last(path: str) -> str:
    if not path:
        return ""
    # path format like $.a[0].b -> last segment "b"
    s = path.replace("]", "").replace("[", ".").replace(".", ".")
    parts = [p for p in s.split(".") if p and p != "$"]
    return parts[-1] if parts else ""


def resolve_tolerance(
    path: str,
    tolerances: Optional[Mapping[str, Any]] = None,
    default: Tolerance = Tolerance(),
) -> Tolerance:
    if not tolerances:
        return default
    if path in tolerances:
        return Tolerance.coerce(tolerances[path])
    last = _path_last(path)
    if last and last in tolerances:
        return Tolerance.coerce(tolerances[last])
    if "*" in tolerances:
        return Tolerance.coerce(tolerances["*"])
    return default


def numeric_close(a: Any, b: Any, tol: Tolerance) -> bool:
    if _is_number(a) and _is_number(b):
        af, bf = float(a), float(b)
        if math.isnan(af) and math.isnan(bf):
            return True
        if math.isinf(af) or math.isinf(bf):
            return af == bf
        return abs(af - bf) <= max(tol.atol, tol.rtol * max(abs(af), abs(bf)))
    return a == b
def _match_list_order(
    actual: Sequence[Any], expected: Sequence[Any], seed: int
) -> Tuple[List[Any], List[Any]]:
    """Deterministically align list elements when possible.

    Strategy:
      - If elements are mappings sharing a common identifier key, align by that key.
      - If duplicates under the same id exist, use `seed` for deterministic tie-breaking.
      - Otherwise, preserve original order.
    """
    if len(actual) != len(expected) or not actual:
        return list(actual), list(expected)
    if not (isinstance(actual[0], Mapping) and isinstance(expected[0], Mapping)):
        return list(actual), list(expected)

    id_keys = ("id", "name", "key", "observable")
    key = next((k for k in id_keys if k in actual[0] and k in expected[0]), None)
    if not key:
        return list(actual), list(expected)

    def buckets(seq: Sequence[Mapping[str, Any]]) -> Dict[str, List[Mapping[str, Any]]]:
        out: Dict[str, List[Mapping[str, Any]]] = {}
        for item in seq:
            out.setdefault(str(item.get(key)), []).append(item)
        return out

    a_b, e_b = buckets(actual), buckets(expected)
    if set(a_b) != set(e_b):
        return list(actual), list(expected)

    rng = random.Random(seed)
    aligned_a: List[Any] = []
    aligned_e: List[Any] = []
    for k in sorted(e_b.keys()):
        ea, aa = e_b[k], a_b[k]
        if len(ea) != len(aa):
            return list(actual), list(expected)
        idxs = list(range(len(ea)))
        rng.shuffle(idxs)
        for i in idxs:
            aligned_e.append(ea[i])
            aligned_a.append(aa[i])
    return aligned_a, aligned_e
def diff(
    actual: Any,
    expected: Any,
    tolerances: Optional[Mapping[str, Any]] = None,
    *,
    seed: int = 0,
    path: str = "$",
) -> List[Dict[str, Any]]:
    """Compute structured differences between `actual` and `expected`."""
    diffs: List[Dict[str, Any]] = []

    def rec(a: Any, e: Any, p: str) -> None:
        tol = resolve_tolerance(p, tolerances)
        if _is_number(a) and _is_number(e):
            if not numeric_close(a, e, tol):
                diffs.append(
                    {"path": p, "actual": a, "expected": e, "atol": tol.atol, "rtol": tol.rtol}
                )
            return

        if isinstance(e, Mapping) and isinstance(a, Mapping):
            keys = sorted(set(a.keys()) | set(e.keys()))
            for k in keys:
                np = f"{p}.{k}"
                if k not in a:
                    diffs.append({"path": np, "actual": None, "expected": e.get(k), "missing": "actual"})
                elif k not in e:
                    diffs.append({"path": np, "actual": a.get(k), "expected": None, "missing": "expected"})
                else:
                    rec(a[k], e[k], np)
            return

        if (
            isinstance(e, Sequence)
            and not isinstance(e, (str, bytes))
            and isinstance(a, Sequence)
            and not isinstance(a, (str, bytes))
        ):
            if len(a) != len(e):
                diffs.append({"path": p, "actual_len": len(a), "expected_len": len(e)})
                return
            aa, ee = _match_list_order(a, e, seed=seed)
            for i, (ai, ei) in enumerate(zip(aa, ee)):
                rec(ai, ei, f"{p}[{i}]")
            return

        if a != e:
            diffs.append({"path": p, "actual": a, "expected": e})

    rec(actual, expected, path)
    return diffs


def compare(
    actual: Any, expected: Any, tolerances: Optional[Mapping[str, Any]] = None, *, seed: int = 0
) -> bool:
    return not diff(actual, expected, tolerances, seed=seed)
def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Compare benchmark outputs with numeric tolerances.")
    p.add_argument("actual_json")
    p.add_argument("expected_json")
    p.add_argument("--tolerances", help="JSON object of tolerances keyed by path/name/'*'.")
    p.add_argument("--seed", type=int, default=0, help="Seed for deterministic tie-breaking.")
    p.add_argument("--diff", action="store_true", help="Print JSON diff on mismatch.")
    args = p.parse_args(list(argv) if argv is not None else None)

    actual = load_json(args.actual_json)
    expected = load_json(args.expected_json)
    tolerances = json.loads(args.tolerances) if args.tolerances else None

    d = diff(actual, expected, tolerances, seed=args.seed)
    ok = not d
    if not ok and args.diff:
        print(json.dumps(d, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
