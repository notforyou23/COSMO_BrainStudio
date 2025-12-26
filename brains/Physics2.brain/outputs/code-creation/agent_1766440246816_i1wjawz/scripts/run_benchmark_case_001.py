#!/usr/bin/env python3
"""End-to-end runner for benchmark_case_001.

- Enforces deterministic settings (RNG seeds, hash seed) for reproducible CI runs.
- Executes benchmark_case_001 (best-effort import, with a deterministic fallback).
- Writes *canonicalized* actual output JSON (stable ordering/float formatting).
- Invokes the integrated comparator against expected/benchmark_case_001.expected.json.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict

from src.determinism import DeterminismPolicy, deterministic_run
from src.stable_json import canonicalize, write_text
from src.benchmark_compare import compare_files, parse_overrides

DEFAULT_SEED = int(os.environ.get("BENCHMARK_SEED", "0"))
DEFAULT_ATOL = float(os.environ.get("BENCHMARK_ATOL", "1e-8"))
DEFAULT_RTOL = float(os.environ.get("BENCHMARK_RTOL", "1e-6"))

def _run_case_001(seed: int) -> Any:
    """Run the benchmark. Uses project implementation if present; else fallback."""
    try:
        # Preferred: project-defined benchmark implementation.
        from src.benchmark_case_001 import run as run_impl  # type: ignore
        return run_impl(seed=seed)
    except Exception:
        pass

    # Deterministic fallback output (keeps this runner functional in isolation).
    import random
    out: Dict[str, Any] = {"benchmark": "benchmark_case_001", "seed": seed}
    rng = random.Random(seed)
    out["python_random_probe"] = [rng.random(), rng.random(), rng.randint(0, 10**9)]
    try:
        import numpy as np  # type: ignore
        rs = np.random.RandomState(seed)
        out["numpy_random_probe"] = [float(rs.rand()), float(rs.rand()), int(rs.randint(0, 10**9))]
    except Exception:
        out["numpy_random_probe"] = None
    return out

def main(argv: list[str] | None = None) -> int:
    here = Path(__file__).resolve()
    repo_root = here.parents[1]
    default_expected = repo_root / "expected" / "benchmark_case_001.expected.json"
    default_actual = repo_root / "actual" / "benchmark_case_001.actual.json"
    default_report = repo_root / "actual" / "benchmark_case_001.diff_report.json"

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--expected", type=Path, default=default_expected)
    p.add_argument("--actual", type=Path, default=default_actual)
    p.add_argument("--report", type=Path, default=default_report)
    p.add_argument("--atol", type=float, default=DEFAULT_ATOL)
    p.add_argument("--rtol", type=float, default=DEFAULT_RTOL)
    p.add_argument("--tolerances-json", type=str, default=os.environ.get("BENCHMARK_TOLERANCES_JSON"))
    p.add_argument("--no-compare", action="store_true", help="Only write actual output; skip expected-vs-actual compare.")
    args = p.parse_args(argv)

    # Make hash iteration order stable as early as we can (ideally set by CI too).
    os.environ.setdefault("PYTHONHASHSEED", str(args.seed))

    policy = DeterminismPolicy(seed=args.seed, strict=True)
    with deterministic_run(seed=args.seed, strict=True):
        policy.apply()
        policy.validate()
        actual_obj = _run_case_001(args.seed)

    # Canonicalize and write stable JSON (byte-for-byte reproducible).
    args.actual.parent.mkdir(parents=True, exist_ok=True)
    write_text(args.actual, canonicalize(actual_obj))

    if args.no_compare:
        sys.stdout.write(f"WROTE:{args.actual}\n")
        return 0

    overrides = parse_overrides(args.tolerances_json)
    rc = compare_files(
        args.actual,
        args.expected,
        seed=args.seed,
        atol=args.atol,
        rtol=args.rtol,
        overrides=overrides,
        report_path=args.report,
    )
    if rc == 0:
        sys.stdout.write(f"OK:{args.actual}\n")
    return rc

if __name__ == "__main__":
    raise SystemExit(main())
