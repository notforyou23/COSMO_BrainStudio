"""Deterministic, seedable toy experiment CLI.

Run:
  python -m src.goal_33_toy_experiment --seed 0 --out ./outputs/goal_33/
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
from pathlib import Path
from typing import Dict, List, Tuple
SCHEMA_VERSION = 1


def _gauss(rng: random.Random) -> float:
    # Box-Muller transform (deterministic given rng state)
    u1 = max(rng.random(), 1e-12)
    u2 = rng.random()
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def _linreg(x: List[float], y: List[float]) -> Tuple[float, float]:
    n = len(x)
    if n != len(y) or n < 2:
        raise ValueError("x and y must have same length >= 2")
    mx = sum(x) / n
    my = sum(y) / n
    sxx = sum((xi - mx) ** 2 for xi in x)
    if sxx == 0.0:
        raise ValueError("degenerate x variance")
    sxy = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    slope = sxy / sxx
    intercept = my - slope * mx
    return slope, intercept


def _write_fallback_png(path: Path) -> None:
    # Minimal valid 1x1 transparent PNG
    png = bytes.fromhex(
        "89504E470D0A1A0A"
        "0000000D49484452000000010000000108060000001F15C489"
        "0000000A49444154789C6360000002000154A24F5D"
        "0000000049454E44AE426082"
    )
    path.write_bytes(png)
def _make_figure(x: List[float], y: List[float], slope: float, intercept: float, out_png: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # type: ignore

        xs = sorted(x)
        ys_fit = [slope * xi + intercept for xi in xs]
        plt.figure(figsize=(6, 4), dpi=150)
        plt.scatter(x, y, s=12, alpha=0.8, label="data")
        plt.plot(xs, ys_fit, linewidth=2, label="fit")
        plt.title("Goal 33 toy experiment: linear regression")
        plt.xlabel("x")
        plt.ylabel("y")
        plt.legend(loc="best")
        plt.tight_layout()
        out_png.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out_png)
        plt.close()
    except Exception:
        out_png.parent.mkdir(parents=True, exist_ok=True)
        _write_fallback_png(out_png)
def run(seed: int, out_dir: Path, n: int = 200, noise_std: float = 0.1) -> Dict:
    if n < 2:
        raise ValueError("--n must be >= 2")
    if noise_std < 0:
        raise ValueError("--noise-std must be >= 0")

    rng = random.Random(int(seed))
    true_slope, true_intercept = 2.0, 1.0

    x = [rng.random() for _ in range(n)]
    y = [true_slope * xi + true_intercept + noise_std * _gauss(rng) for xi in x]

    slope, intercept = _linreg(x, y)
    yhat = [slope * xi + intercept for xi in x]
    mse = sum((yi - yhi) ** 2 for yi, yhi in zip(y, yhat)) / n

    out_dir.mkdir(parents=True, exist_ok=True)
    results_json = out_dir / "results.json"
    figure_png = out_dir / "figure.png"
    _make_figure(x, y, slope, intercept, figure_png)

    payload = {
        "schema_version": SCHEMA_VERSION,
        "seed": int(seed),
        "parameters": {"n": int(n), "noise_std": float(noise_std)},
        "truth": {"slope": true_slope, "intercept": true_intercept},
        "fit": {"slope": float(slope), "intercept": float(intercept)},
        "metrics": {"mse": float(mse)},
        "artifacts": {
            "results_json": str(results_json.name),
            "figure_png": str(figure_png.name),
        },
    }
    results_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if not results_json.is_file():
        raise RuntimeError("results.json was not written")
    if not figure_png.is_file():
        raise RuntimeError("figure.png was not written")

    return payload
def _parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Deterministic toy experiment (Goal 33).")
    p.add_argument("--seed", type=int, default=0, help="RNG seed (int).")
    p.add_argument("--out", type=str, required=True, help="Output directory.")
    p.add_argument("--n", type=int, default=200, help="Number of samples (>=2).")
    p.add_argument("--noise-std", type=float, default=0.1, help="Gaussian noise std (>=0).")
    return p.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        args = _parse_args(argv)
        out_dir = Path(args.out)
        payload = run(seed=args.seed, out_dir=out_dir, n=args.n, noise_std=args.noise_std)
        print(json.dumps({"ok": True, "out": str(out_dir), "schema_version": payload["schema_version"]}))
        return 0
    except SystemExit:
        raise
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
