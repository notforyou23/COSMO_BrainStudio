"""Deterministic benchmark reproduction helpers.

This module is intentionally dependency-light so it can be used by both a CLI
wrapper and pytest to reproduce a known benchmark case and emit JSON output.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from hashlib import sha256
from math import fsum, sqrt
from pathlib import Path
from typing import Any, Dict, Optional
import json
import os
import random
def _seed_everything(seed: int) -> None:
    """Seed common RNGs for deterministic runs."""
    random.seed(seed)
    # Numpy is optional; if present, seed it as well.
    try:
        import numpy as np  # type: ignore
    except Exception:
        np = None
    if np is not None:
        np.random.seed(seed)
    # Best-effort: keep other libs deterministic if they are imported later.
    os.environ.setdefault("PYTHONHASHSEED", str(seed))
@dataclass(frozen=True)
class Case001Config:
    n: int = 1024
    d: int = 8
    noise_std: float = 0.05

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
def _dot(a: list[float], b: list[float]) -> float:
    return fsum(x * y for x, y in zip(a, b))


def _l2(a: list[float]) -> float:
    return sqrt(fsum(x * x for x in a))
def run_benchmark_case_001(seed: int = 0, config: Optional[Case001Config] = None) -> Dict[str, Any]:
    """Run benchmark_case_001 deterministically and return a JSON-serializable dict."""
    cfg = config or Case001Config()
    _seed_everything(seed)
    rng = random.Random(seed)

    # Ground-truth weights and bias.
    w_true = [rng.uniform(-1.0, 1.0) for _ in range(cfg.d)]
    b_true = rng.uniform(-0.5, 0.5)

    # A simple fixed estimator: ridge-like shrinkage of true weights.
    shrink = 0.85
    w_hat = [shrink * w for w in w_true]
    b_hat = b_true * shrink

    # Generate data and evaluate predictions.
    sq_errs: list[float] = []
    abs_errs: list[float] = []
    y_samples: list[float] = []

    for _ in range(cfg.n):
        x = [rng.gauss(0.0, 1.0) for _ in range(cfg.d)]
        noise = rng.gauss(0.0, cfg.noise_std)
        y = _dot(w_true, x) + b_true + noise
        y_hat = _dot(w_hat, x) + b_hat
        err = y_hat - y
        sq_errs.append(err * err)
        abs_errs.append(abs(err))
        if len(y_samples) < 16:
            y_samples.append(y)

    mse = fsum(sq_errs) / cfg.n
    rmse = sqrt(mse)
    mae = fsum(abs_errs) / cfg.n

    digest = sha256(
        json.dumps(
            {
                "w_true": w_true,
                "b_true": b_true,
                "w_hat": w_hat,
                "b_hat": b_hat,
                "y_samples": y_samples,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    return {
        "case_id": "benchmark_case_001",
        "seed": seed,
        "config": cfg.to_dict(),
        "metrics": {"mse": mse, "rmse": rmse, "mae": mae},
        "artifacts": {
            "w_true_l2": _l2(w_true),
            "w_hat_l2": _l2(w_hat),
            "sample_digest_sha256": digest,
            "y_samples": y_samples,
        },
    }
def reproduce(case_id: str, *, seed: int = 0) -> Dict[str, Any]:
    """Reproduce a supported benchmark case."""
    if case_id != "benchmark_case_001":
        raise ValueError(f"Unsupported case_id: {case_id!r}")
    return run_benchmark_case_001(seed=seed)
def write_json(data: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
def verify_against_expected(
    produced: Dict[str, Any],
    expected_path: Path,
    *,
    rtol: float = 1e-7,
    atol: float = 1e-9,
) -> None:
    """Verify produced output against expected JSON using tolerant comparison.

    Uses src.benchmark.json_compare if available; otherwise falls back to strict
    equality for non-floats and tight float tolerance.
    """
    expected = json.loads(expected_path.read_text(encoding="utf-8"))

    try:
        from .json_compare import assert_json_close  # type: ignore
    except Exception:
        assert_json_close = None  # type: ignore

    if assert_json_close is not None:
        assert_json_close(produced, expected, rtol=rtol, atol=atol)
        return

    def _close(a: Any, b: Any) -> bool:
        if isinstance(a, (int, str, bool)) or a is None:
            return a == b
        if isinstance(a, float) and isinstance(b, float):
            return abs(a - b) <= (atol + rtol * abs(b))
        if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
            return all(_close(x, y) for x, y in zip(a, b))
        if isinstance(a, dict) and isinstance(b, dict) and a.keys() == b.keys():
            return all(_close(a[k], b[k]) for k in a.keys())
        return a == b

    if not _close(produced, expected):
        raise AssertionError("Produced JSON did not match expected within tolerances.")
def main(argv: Optional[list[str]] = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Reproduce deterministic benchmark outputs.")
    p.add_argument("case_id", choices=["benchmark_case_001"])
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out", type=Path, required=True, help="Output JSON path.")
    p.add_argument("--expected", type=Path, default=None, help="Optional expected JSON to verify against.")
    p.add_argument("--rtol", type=float, default=1e-7)
    p.add_argument("--atol", type=float, default=1e-9)
    ns = p.parse_args(argv)

    produced = reproduce(ns.case_id, seed=ns.seed)
    write_json(produced, ns.out)
    if ns.expected is not None:
        verify_against_expected(produced, ns.expected, rtol=ns.rtol, atol=ns.atol)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
