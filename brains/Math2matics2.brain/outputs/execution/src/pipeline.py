from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

import numpy as np


@dataclass(frozen=True)
class PipelineConfig:
    n: int = 256
    noise_std: float = 0.15
    degree: int = 3
    x_min: float = -3.0
    x_max: float = 3.0


def generate_data(rng: np.random.Generator, cfg: PipelineConfig) -> Dict[str, np.ndarray]:
    x = np.linspace(cfg.x_min, cfg.x_max, cfg.n, dtype=np.float64)
    y_true = np.sin(x)
    noise = rng.normal(loc=0.0, scale=cfg.noise_std, size=cfg.n).astype(np.float64)
    y = y_true + noise
    return {"x": x, "y": y, "y_true": y_true}


def fit_polynomial(x: np.ndarray, y: np.ndarray, degree: int) -> np.ndarray:
    coeffs = np.polyfit(x, y, deg=int(degree)).astype(np.float64)
    return coeffs


def predict_polynomial(x: np.ndarray, coeffs: np.ndarray) -> np.ndarray:
    return np.polyval(coeffs, x).astype(np.float64)


def compute_metrics(y: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    y = np.asarray(y, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)
    resid = y - y_pred
    mse = float(np.mean(resid * resid))
    mae = float(np.mean(np.abs(resid)))
    var = float(np.var(y))
    r2 = float("nan") if var == 0.0 else float(1.0 - mse / var)
    return {"mse": mse, "mae": mae, "r2": r2}


def make_figure(
    x: np.ndarray,
    y: np.ndarray,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    cfg: PipelineConfig,
):
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 4), dpi=150)
    ax.scatter(x, y, s=10, alpha=0.6, label="observed", color="#1f77b4")
    ax.plot(x, y_true, lw=2, label="true: sin(x)", color="#2ca02c")
    ax.plot(x, y_pred, lw=2, label=f"poly deg={cfg.degree}", color="#d62728")
    ax.set_title("Deterministic canonical pipeline")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best", frameon=False)
    fig.tight_layout()
    return fig


def run_pipeline(
    rng: np.random.Generator, cfg: PipelineConfig | None = None
) -> Tuple[Dict[str, Any], Any]:
    cfg = cfg or PipelineConfig()
    data = generate_data(rng, cfg)
    coeffs = fit_polynomial(data["x"], data["y"], cfg.degree)
    y_pred = predict_polynomial(data["x"], coeffs)
    metrics = compute_metrics(data["y"], y_pred)

    results: Dict[str, Any] = {
        "schema_version": 1,
        "config": {
            "n": int(cfg.n),
            "noise_std": float(cfg.noise_std),
            "degree": int(cfg.degree),
            "x_min": float(cfg.x_min),
            "x_max": float(cfg.x_max),
        },
        "model": {"type": "polynomial_regression", "coeffs": [float(c) for c in coeffs.tolist()]},
        "metrics": {k: float(v) for k, v in metrics.items()},
        "examples": {
            "x0": float(data["x"][0]),
            "y0": float(data["y"][0]),
            "y_pred0": float(y_pred[0]),
            "x_last": float(data["x"][-1]),
            "y_last": float(data["y"][-1]),
            "y_pred_last": float(y_pred[-1]),
        },
    }

    fig = make_figure(data["x"], data["y"], data["y_true"], y_pred, cfg)
    return results, fig
