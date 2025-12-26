from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Tuple

import numpy as np


@dataclass(frozen=True)
class PipelineConfig:
    n: int = 256
    x_min: float = -2.0
    x_max: float = 2.0
    true_intercept: float = 0.5
    true_slope: float = 1.7
    noise_std: float = 0.25
    n_bins: int = 24


def generate_data(cfg: PipelineConfig, rng: np.random.Generator) -> Dict[str, np.ndarray]:
    x = rng.uniform(cfg.x_min, cfg.x_max, size=cfg.n).astype(np.float64)
    eps = rng.normal(0.0, cfg.noise_std, size=cfg.n).astype(np.float64)
    y = (cfg.true_intercept + cfg.true_slope * x + eps).astype(np.float64)
    idx = np.argsort(x)
    return {"x": x[idx], "y": y[idx]}


def fit_linear_regression(data: Dict[str, np.ndarray]) -> Dict[str, float]:
    x = np.asarray(data["x"], dtype=np.float64)
    y = np.asarray(data["y"], dtype=np.float64)
    X = np.column_stack([np.ones_like(x), x])
    beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    return {"intercept": float(beta[0]), "slope": float(beta[1])}


def predict(model: Dict[str, float], x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    return model["intercept"] + model["slope"] * x


def compute_metrics(data: Dict[str, np.ndarray], model: Dict[str, float]) -> Dict[str, float]:
    x = np.asarray(data["x"], dtype=np.float64)
    y = np.asarray(data["y"], dtype=np.float64)
    yhat = predict(model, x)
    resid = y - yhat
    mse = float(np.mean(resid * resid))
    rmse = float(np.sqrt(mse))
    mae = float(np.mean(np.abs(resid)))
    sst = float(np.sum((y - float(np.mean(y))) ** 2))
    ssr = float(np.sum((y - yhat) ** 2))
    r2 = float(1.0 - (ssr / sst if sst > 0 else 0.0))
    return {"mse": mse, "rmse": rmse, "mae": mae, "r2": r2}


def summarize_data(data: Dict[str, np.ndarray]) -> Dict[str, Any]:
    x = np.asarray(data["x"], dtype=np.float64)
    y = np.asarray(data["y"], dtype=np.float64)
    return {
        "n": int(x.size),
        "x_min": float(np.min(x)),
        "x_max": float(np.max(x)),
        "y_mean": float(np.mean(y)),
        "y_std": float(np.std(y, ddof=0)),
    }


def create_figure(cfg: PipelineConfig, data: Dict[str, np.ndarray], model: Dict[str, float]) -> Any:
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    x = np.asarray(data["x"], dtype=np.float64)
    y = np.asarray(data["y"], dtype=np.float64)
    yhat = predict(model, x)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7.0, 7.0), dpi=150, constrained_layout=True)

    ax1.scatter(x, y, s=10, alpha=0.7, linewidths=0.0, label="data")
    ax1.plot(x, yhat, color="C1", linewidth=2.0, label="fit")
    ax1.set_title("Deterministic Linear Regression Pipeline")
    ax1.set_xlabel("x")
    ax1.set_ylabel("y")
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="best", frameon=False)

    resid = y - yhat
    ax2.hist(resid, bins=int(cfg.n_bins), color="C2", alpha=0.8, edgecolor="white")
    ax2.set_xlabel("residual")
    ax2.set_ylabel("count")
    ax2.grid(True, alpha=0.3)

    return fig


def run_pipeline(cfg: PipelineConfig, rng: np.random.Generator) -> Tuple[Dict[str, Any], Any]:
    data = generate_data(cfg, rng)
    model = fit_linear_regression(data)
    metrics = compute_metrics(data, model)
    fig = create_figure(cfg, data, model)

    results: Dict[str, Any] = {
        "schema_version": 1,
        "config": asdict(cfg),
        "data_summary": summarize_data(data),
        "model": {"intercept": float(model["intercept"]), "slope": float(model["slope"])},
        "metrics": {k: float(v) for k, v in metrics.items()},
    }
    return results, fig
