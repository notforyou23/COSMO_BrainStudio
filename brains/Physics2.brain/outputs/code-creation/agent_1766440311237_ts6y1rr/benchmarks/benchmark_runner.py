"""Benchmark runner with deterministic execution and tolerance-aware comparison.

This runner is intentionally small: it applies a single determinism policy, runs a
benchmark case module, and compares expected vs actual using numeric tolerances.
"""

from __future__ import annotations

import argparse
import importlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from src.determinism_policy import apply_determinism_policy
from src.numeric_diff import DiffResult, diff
from src.stable_json import stable_dumps
@dataclass(frozen=True)
class Tolerances:
    atol: float = 0.0
    rtol: float = 0.0

    @classmethod
    def from_env(cls) -> "Tolerances":
        def f(name: str, default: float) -> float:
            v = os.environ.get(name)
            return default if v is None or v == "" else float(v)
        return cls(atol=f("BENCH_ATOL", 0.0), rtol=f("BENCH_RTOL", 0.0))
def _ensure_repo_on_path() -> None:
    # Allow `python benchmarks/benchmark_runner.py` from repo root or elsewhere.
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
def _load_case(case_name: str):
    _ensure_repo_on_path()
    return importlib.import_module(f"benchmarks.cases.{case_name}")
def _run_case_module(mod, seed: int) -> Tuple[Any, Any, Dict[str, Any]]:
    """Return (expected, actual, metadata) from a case module.

    Supported case APIs (checked in this order):
    - mod.run(seed=..., stable_dumps=...): returns dict with keys expected/actual
    - mod.get_expected()/mod.get_actual()
    - mod.expected and mod.actual attributes
    """
    meta: Dict[str, Any] = {"case_module": getattr(mod, "__name__", str(mod))}
    if hasattr(mod, "run") and callable(mod.run):
        out = mod.run(seed=seed, stable_dumps=stable_dumps)
        if isinstance(out, dict) and "expected" in out and "actual" in out:
            meta.update({k: v for k, v in out.items() if k not in ("expected", "actual")})
            return out["expected"], out["actual"], meta
    if all(hasattr(mod, n) and callable(getattr(mod, n)) for n in ("get_expected", "get_actual")):
        return mod.get_expected(), mod.get_actual(), meta
    if hasattr(mod, "expected") and hasattr(mod, "actual"):
        return getattr(mod, "expected"), getattr(mod, "actual"), meta
    raise TypeError(
        f"Unsupported benchmark case API for {meta['case_module']}. "
        "Expected run() or get_expected/get_actual or expected/actual."
    )
def compare_expected_actual(expected: Any, actual: Any, tolerances: Tolerances) -> DiffResult:
    return diff(expected, actual, atol=tolerances.atol, rtol=tolerances.rtol)
def run_case(case_name: str, seed: int, tolerances: Optional[Tolerances] = None) -> int:
    tolerances = tolerances or Tolerances.from_env()
    apply_determinism_policy(seed=seed)

    mod = _load_case(case_name)
    expected, actual, meta = _run_case_module(mod, seed=seed)

    # Deterministic, stable renderings are useful for debug logs.
    exp_s = stable_dumps(expected)
    act_s = stable_dumps(actual)

    result = compare_expected_actual(expected, actual, tolerances)
    if result.ok:
        return 0

    # Keep output concise but actionable.
    sys.stderr.write(f"CASE_FAILED:{case_name}\n")
    sys.stderr.write(f"SEED:{seed} ATOL:{tolerances.atol} RTOL:{tolerances.rtol}\n")
    if meta:
        sys.stderr.write(f"META:{stable_dumps(meta)}\n")
    sys.stderr.write(f"MISMATCH:{result.message}\n")
    # Include stable JSON for small payloads only.
    if len(exp_s) <= 10_000 and len(act_s) <= 10_000:
        sys.stderr.write(f"EXPECTED:{exp_s}\n")
        sys.stderr.write(f"ACTUAL:{act_s}\n")
    return 1
def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Deterministic benchmark runner")
    p.add_argument("--case", default="benchmark_case_001", help="Case module name under benchmarks/cases/")
    p.add_argument("--seed", type=int, default=int(os.environ.get("BENCH_SEED", "0")))
    p.add_argument("--atol", type=float, default=None)
    p.add_argument("--rtol", type=float, default=None)
    args = p.parse_args(argv)

    tol = Tolerances.from_env()
    if args.atol is not None or args.rtol is not None:
        tol = Tolerances(atol=tol.atol if args.atol is None else args.atol,
                         rtol=tol.rtol if args.rtol is None else args.rtol)
    return run_case(args.case, seed=args.seed, tolerances=tol)


if __name__ == "__main__":
    raise SystemExit(main())
