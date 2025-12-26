"""Toy experiment: deterministic synthetic regression with optional plot.

Exposes `run_toy_experiment(...)` which returns a metrics dict and optionally saves
a plot as `figure.png` in the provided output directory.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import math

import numpy as np
@dataclass(frozen=True)
class ToyExperimentConfig:
    seed: int = 0
    n: int = 256
    noise_std: float = 0.25
    true_slope: float = 1.75
    true_intercept: float = -0.4
    plot: bool = True


def _linear_fit(x: np.ndarray, y: np.ndarray) -> Tuple[float, float]:
    x = np.asarray(x, dtype=float).reshape(-1)
    y = np.asarray(y, dtype=float).reshape(-1)
    x_mean = float(x.mean())
    y_mean = float(y.mean())
    denom = float(((x - x_mean) ** 2).sum())
    slope = 0.0 if denom == 0.0 else float(((x - x_mean) * (y - y_mean)).sum() / denom)
    intercept = y_mean - slope * x_mean
    return slope, intercept


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    y_true = np.asarray(y_true, dtype=float).reshape(-1)
    y_pred = np.asarray(y_pred, dtype=float).reshape(-1)
    resid = y_true - y_pred
    mse = float(np.mean(resid**2))
    rmse = float(math.sqrt(mse))
    var = float(np.var(y_true))
    r2 = float("nan") if var == 0.0 else float(1.0 - mse / var)
    return {"mse": mse, "rmse": rmse, "r2": r2}
def run_toy_experiment(
    output_dir: str | Path,
    config: Optional[ToyExperimentConfig] = None,
) -> Dict[str, Any]:
    cfg = config or ToyExperimentConfig()
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(int(cfg.seed))
    x = rng.uniform(-2.0, 2.0, size=int(cfg.n))
    noise = rng.normal(0.0, float(cfg.noise_std), size=int(cfg.n))
    y = float(cfg.true_slope) * x + float(cfg.true_intercept) + noise

    slope, intercept = _linear_fit(x, y)
    y_hat = slope * x + intercept
    m = _metrics(y, y_hat)

    fig_path = None
    if bool(cfg.plot):
        try:
            import matplotlib

            matplotlib.use("Agg", force=True)
            import matplotlib.pyplot as plt

            order = np.argsort(x)
            xs = x[order]
            ys = y[order]
            yhs = y_hat[order]

            plt.figure(figsize=(6.4, 4.0))
            plt.scatter(x, y, s=14, alpha=0.75, label="data")
            plt.plot(xs, yhs, linewidth=2.0, label="fit")
            plt.title("Toy linear regression")
            plt.xlabel("x")
            plt.ylabel("y")
            plt.legend(loc="best")
            plt.tight_layout()
            fig_path = out_dir / "figure.png"
            plt.savefig(fig_path, dpi=150)
            plt.close()
        except Exception:
            fig_path = None

    return {
        "config": {
            "seed": int(cfg.seed),
            "n": int(cfg.n),
            "noise_std": float(cfg.noise_std),
            "true_slope": float(cfg.true_slope),
            "true_intercept": float(cfg.true_intercept),
            "plot": bool(cfg.plot),
        },
        "fit": {"slope": float(slope), "intercept": float(intercept)},
        "metrics": m,
        "artifacts": {"figure.png": str(fig_path) if fig_path else None},
    }


if __name__ == "__main__":
    import argparse
    import json as _json

    p = argparse.ArgumentParser()
    p.add_argument("--output_dir", type=str, default="outputs")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--n", type=int, default=256)
    p.add_argument("--noise_std", type=float, default=0.25)
    p.add_argument("--plot", action="store_true")
    p.add_argument("--no-plot", dest="plot", action="store_false")
    p.set_defaults(plot=True)
    args = p.parse_args()

    res = run_toy_experiment(
        args.output_dir,
        ToyExperimentConfig(seed=args.seed, n=args.n, noise_std=args.noise_std, plot=args.plot),
    )
    print(_json.dumps(res, indent=2, sort_keys=True))
