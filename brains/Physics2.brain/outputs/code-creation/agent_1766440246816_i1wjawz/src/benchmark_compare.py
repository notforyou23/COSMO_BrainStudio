#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple, Union

Number = Union[int, float]
def enforce_determinism(seed: int) -> None:
    # Best-effort determinism for benchmark runs and comparisons.
    random.seed(seed)
    os.environ.setdefault("PYTHONHASHSEED", str(seed))
    try:
        import numpy as np  # type: ignore
        np.random.seed(seed)
    except Exception:
        pass
def canonical_dumps(obj: Any) -> str:
    # Stable JSON for CI logs/artifacts (key ordering, normalized whitespace).
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _path_join(base: str, key: Union[str, int]) -> str:
    if isinstance(key, int):
        return f"{base}[{key}]"
    # JSON-pointer-ish but human friendly.
    return f"{base}.{key}" if base else str(key)
@dataclass
class Diff:
    path: str
    expected: Any
    actual: Any
    message: str

    def as_dict(self) -> Dict[str, Any]:
        return {"path": self.path, "expected": self.expected, "actual": self.actual, "message": self.message}
def _tol_for_path(path: str, base_atol: float, base_rtol: float, overrides: Dict[str, Dict[str, float]]) -> Tuple[float, float]:
    if path in overrides:
        o = overrides[path]
        return float(o.get("atol", base_atol)), float(o.get("rtol", base_rtol))
    return base_atol, base_rtol


def numbers_close(a: Number, b: Number, atol: float, rtol: float) -> bool:
    # NaN==NaN, inf must match sign.
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, float) and math.isnan(a):
        return isinstance(b, float) and math.isnan(b)
    if isinstance(b, float) and math.isnan(b):
        return False
    if isinstance(a, float) and math.isinf(a) or isinstance(b, float) and math.isinf(b):
        return a == b
    return abs(a - b) <= (atol + rtol * abs(b))
def diff_json(
    expected: Any,
    actual: Any,
    *,
    atol: float = 1e-8,
    rtol: float = 1e-6,
    overrides: Dict[str, Dict[str, float]] | None = None,
    path: str = "",
) -> List[Diff]:
    overrides = overrides or {}
    diffs: List[Diff] = []

    if _is_number(expected) and _is_number(actual):
        pa_atol, pa_rtol = _tol_for_path(path, atol, rtol, overrides)
        if not numbers_close(float(expected), float(actual), pa_atol, pa_rtol):
            diffs.append(Diff(path, expected, actual, f"numbers differ (atol={pa_atol}, rtol={pa_rtol})"))
        return diffs

    if type(expected) != type(actual):
        diffs.append(Diff(path, expected, actual, f"type mismatch: {type(expected).__name__} vs {type(actual).__name__}"))
        return diffs

    if isinstance(expected, dict):
        ekeys, akeys = set(expected.keys()), set(actual.keys())  # type: ignore[arg-type]
        for k in sorted(ekeys - akeys):
            diffs.append(Diff(_path_join(path, str(k)), expected[k], None, "missing key in actual"))  # type: ignore[index]
        for k in sorted(akeys - ekeys):
            diffs.append(Diff(_path_join(path, str(k)), None, actual[k], "extra key in actual"))  # type: ignore[index]
        for k in sorted(ekeys & akeys):
            diffs.extend(diff_json(expected[k], actual[k], atol=atol, rtol=rtol, overrides=overrides, path=_path_join(path, str(k))))  # type: ignore[index]
        return diffs

    if isinstance(expected, list):
        if len(expected) != len(actual):  # type: ignore[arg-type]
            diffs.append(Diff(path, len(expected), len(actual), "list length differs"))
        for i, (e, a) in enumerate(zip(expected, actual)):  # type: ignore[arg-type]
            diffs.extend(diff_json(e, a, atol=atol, rtol=rtol, overrides=overrides, path=_path_join(path, i)))
        return diffs

    if expected != actual:
        diffs.append(Diff(path, expected, actual, "value differs"))
    return diffs
def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_overrides(raw: str | None) -> Dict[str, Dict[str, float]]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return {str(k): dict(v) for k, v in data.items() if isinstance(v, dict)}
    except Exception:
        pass
    raise ValueError("Invalid tolerances JSON; expected object mapping path-> {atol, rtol}")


def compare_files(
    actual_path: Path,
    expected_path: Path,
    *,
    seed: int = 0,
    atol: float = 1e-8,
    rtol: float = 1e-6,
    overrides: Dict[str, Dict[str, float]] | None = None,
    report_path: Path | None = None,
) -> int:
    enforce_determinism(seed)
    try:
        expected = load_json(expected_path)
        actual = load_json(actual_path)
    except Exception as e:
        sys.stderr.write(f"ERROR: failed to load JSON: {e}\n")
        return 2

    diffs = diff_json(expected, actual, atol=atol, rtol=rtol, overrides=overrides or {})
    report = {
        "ok": not diffs,
        "seed": seed,
        "atol": atol,
        "rtol": rtol,
        "expected_path": str(expected_path),
        "actual_path": str(actual_path),
        "diff_count": len(diffs),
        "diffs": [d.as_dict() for d in diffs[:200]],
        "truncated": len(diffs) > 200,
    }
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(canonical_dumps(report), encoding="utf-8")

    if diffs:
        sys.stderr.write(f"FAIL: {len(diffs)} diffs\n")
        sys.stderr.write(canonical_dumps(report if len(diffs) <= 20 else {**report, "diffs": report["diffs"][:20], "truncated": True}))
        return 1
    sys.stdout.write("PASS\n")
    return 0
def main(argv: List[str] | None = None) -> int:
    here = Path(__file__).resolve()
    default_expected = here.parents[1] / "expected" / "benchmark_case_001.expected.json"

    p = argparse.ArgumentParser(description="Benchmark expected-vs-actual JSON comparator with determinism + numeric tolerances.")
    p.add_argument("--actual", type=Path, required=True, help="Path to actual benchmark JSON output.")
    p.add_argument("--expected", type=Path, default=default_expected, help=f"Path to expected JSON (default: {default_expected})")
    p.add_argument("--seed", type=int, default=int(os.environ.get("BENCHMARK_SEED", "0")))
    p.add_argument("--atol", type=float, default=float(os.environ.get("BENCHMARK_ATOL", "1e-8")))
    p.add_argument("--rtol", type=float, default=float(os.environ.get("BENCHMARK_RTOL", "1e-6")))
    p.add_argument("--tolerances-json", type=str, default=os.environ.get("BENCHMARK_TOLERANCES_JSON"))
    p.add_argument("--report", type=Path, default=None, help="Optional path to write a canonical JSON report for CI artifacts.")
    args = p.parse_args(argv)

    overrides = parse_overrides(args.tolerances_json)
    return compare_files(
        args.actual,
        args.expected,
        seed=args.seed,
        atol=args.atol,
        rtol=args.rtol,
        overrides=overrides,
        report_path=args.report,
    )


if __name__ == "__main__":
    raise SystemExit(main())
