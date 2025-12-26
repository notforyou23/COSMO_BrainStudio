from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import math

import numpy as np
import matplotlib
matplotlib.use("Agg")  # headless / deterministic
import matplotlib.pyplot as plt


@dataclass(frozen=True)
class ExperimentResult:
    seed: int
    n_samples: int
    true_weight: float
    true_bias: float
    noise_std: float
    learned_weight: float
    learned_bias: float
    mse: float
    r2: float
    outputs_dir: str
    metrics_path: str
    plot_path: str


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _outputs_dir(outputs_dir: str | Path | None = None) -> Path:
    if outputs_dir is None:
        return _project_root() / "outputs"
    p = Path(outputs_dir)
    return p if p.is_absolute() else _project_root() / p


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def _synthetic_linear(seed: int, n: int, w: float, b: float, noise_std: float) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    x = np.linspace(-1.0, 1.0, n, dtype=np.float64)
    noise = rng.normal(0.0, noise_std, size=n).astype(np.float64)
    y = w * x + b + noise
    return x.reshape(-1, 1), y


def _fit_linear_regression(X: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    ones = np.ones((X.shape[0], 1), dtype=np.float64)
    A = np.concatenate([X.astype(np.float64), ones], axis=1)  # [x, 1]
    theta, *_ = np.linalg.lstsq(A, y.astype(np.float64), rcond=None)
    return float(theta[0]), float(theta[1])


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float]:
    y_true = y_true.astype(np.float64)
    y_pred = y_pred.astype(np.float64)
    mse = float(np.mean((y_true - y_pred) ** 2))
    denom = float(np.sum((y_true - float(np.mean(y_true))) ** 2))
    r2 = 1.0 - float(np.sum((y_true - y_pred) ** 2)) / denom if denom > 0 else float("nan")
    r2 = float(max(-1.0, min(1.0, r2))) if not math.isnan(r2) else r2
    return mse, r2


def _save_plot(path: Path, X: np.ndarray, y: np.ndarray, w_hat: float, b_hat: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    x = X[:, 0]
    x_line = np.linspace(float(np.min(x)), float(np.max(x)), 200)
    y_line = w_hat * x_line + b_hat

    fig, ax = plt.subplots(figsize=(6, 4), dpi=150)
    ax.scatter(x, y, s=12, alpha=0.8, label="data")
    ax.plot(x_line, y_line, color="C1", linewidth=2, label="fit")
    ax.set_title("Toy Linear Regression (Deterministic)")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def run_toy_experiment(
    *,
    seed: int = 7,
    n_samples: int = 64,
    true_weight: float = 3.0,
    true_bias: float = -0.5,
    noise_std: float = 0.1,
    outputs_dir: str | Path | None = None,
) -> ExperimentResult:
    out_dir = _outputs_dir(outputs_dir)
    X, y = _synthetic_linear(seed=seed, n=n_samples, w=true_weight, b=true_bias, noise_std=noise_std)
    w_hat, b_hat = _fit_linear_regression(X, y)
    y_pred = w_hat * X[:, 0] + b_hat
    mse, r2 = _metrics(y, y_pred)

    metrics_path = out_dir / "metrics.json"
    plot_path = out_dir / "fit.png"
    _write_json(
        metrics_path,
        {
            "seed": seed,
            "n_samples": n_samples,
            "true_params": {"weight": true_weight, "bias": true_bias, "noise_std": noise_std},
            "learned_params": {"weight": w_hat, "bias": b_hat},
            "metrics": {"mse": mse, "r2": r2},
            "artifacts": {"plot": str(plot_path.as_posix())},
        },
    )
    _save_plot(plot_path, X, y, w_hat, b_hat)

    return ExperimentResult(
        seed=seed,
        n_samples=n_samples,
        true_weight=true_weight,
        true_bias=true_bias,
        noise_std=noise_std,
        learned_weight=w_hat,
        learned_bias=b_hat,
        mse=mse,
        r2=r2,
        outputs_dir=str(out_dir.as_posix()),
        metrics_path=str(metrics_path.as_posix()),
        plot_path=str(plot_path.as_posix()),
    )


if __name__ == "__main__":
    res = run_toy_experiment()
    print(json.dumps({"metrics_path": res.metrics_path, "plot_path": res.plot_path}, indent=2, sort_keys=True))
