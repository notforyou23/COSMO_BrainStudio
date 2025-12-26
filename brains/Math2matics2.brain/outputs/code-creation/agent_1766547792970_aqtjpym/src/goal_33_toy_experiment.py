from __future__ import annotations

import csv
import json
import math
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None


OUTPUT_DIRNAME = "outputs"


@dataclass(frozen=True)
class ExperimentConfig:
    seed: int = 0
    n: int = 200
    noise_std: float = 0.2


def _set_deterministic_seed(seed: int) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    if np is not None:
        np.random.seed(seed)


def _generate_data(cfg: ExperimentConfig) -> Tuple[List[float], List[float]]:
    if np is not None:
        x = np.linspace(-1.0, 1.0, cfg.n, dtype=float)
        y = np.sin(3.0 * x) + np.random.normal(0.0, cfg.noise_std, size=cfg.n)
        return x.tolist(), y.tolist()

    # Fallback without numpy
    xs = [(-1.0 + 2.0 * i / max(cfg.n - 1, 1)) for i in range(cfg.n)]
    ys = [math.sin(3.0 * x) + random.gauss(0.0, cfg.noise_std) for x in xs]
    return xs, ys


def _fit_linear(xs: List[float], ys: List[float]) -> Tuple[float, float]:
    n = len(xs)
    if n == 0:
        return 0.0, 0.0
    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    sxx = sum((x - x_mean) ** 2 for x in xs)
    sxy = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    if sxx == 0.0:
        return y_mean, 0.0
    b = sxy / sxx
    a = y_mean - b * x_mean
    return a, b


def _predict_linear(a: float, b: float, xs: List[float]) -> List[float]:
    return [a + b * x for x in xs]


def _mse(y_true: List[float], y_pred: List[float]) -> float:
    n = min(len(y_true), len(y_pred))
    if n == 0:
        return 0.0
    return sum((yt - yp) ** 2 for yt, yp in zip(y_true[:n], y_pred[:n])) / n


def run_goal_33_toy_experiment(
    output_dir: Path | str = OUTPUT_DIRNAME,
    seed: int = 0,
    n: int = 200,
    noise_std: float = 0.2,
) -> Dict[str, object]:
    cfg = ExperimentConfig(seed=seed, n=n, noise_std=noise_std)
    _set_deterministic_seed(cfg.seed)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    xs, ys = _generate_data(cfg)
    a, b = _fit_linear(xs, ys)
    yhat = _predict_linear(a, b, xs)
    mse = _mse(ys, yhat)

    metrics = {
        "goal": "goal_33",
        "seed": cfg.seed,
        "n": cfg.n,
        "noise_std": cfg.noise_std,
        "model": {"type": "linear_regression_closed_form", "intercept": a, "slope": b},
        "mse": mse,
    }

    (out_dir / "goal_33_metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with (out_dir / "goal_33_samples.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["x", "y", "y_hat"])
        for x, y, yh in zip(xs, ys, yhat):
            w.writerow([f"{x:.8f}", f"{y:.8f}", f"{yh:.8f}"])

    (out_dir / "goal_33_done.txt").write_text("ok\n", encoding="utf-8")

    return metrics


def main(argv: Optional[List[str]] = None) -> int:
    # Minimal deterministic entrypoint; avoids external dependencies and writes artifacts into ./outputs/.
    seed = 0
    n = 200
    noise_std = 0.2
    _ = run_goal_33_toy_experiment(output_dir=OUTPUT_DIRNAME, seed=seed, n=n, noise_std=noise_std)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
