from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import json
import math
import random
import hashlib

try:
    import numpy as np  # type: ignore
except Exception:  # pragma: no cover
    np = None  # type: ignore


DEFAULT_SEED = 1337


def set_global_determinism(seed: int = DEFAULT_SEED) -> Dict[str, Any]:
    """Set deterministic RNG state for stdlib and numpy (if present)."""
    random.seed(int(seed))
    info: Dict[str, Any] = {"seed": int(seed), "numpy_available": bool(np)}
    if np is not None:
        np.random.seed(int(seed))
    return info


def _stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _as_float_list(x: Any) -> list:
    if np is not None and isinstance(x, np.ndarray):
        return [float(v) for v in x.tolist()]
    return [float(v) for v in x]


def generate_synthetic_regression(
    n: int = 256, seed: int = DEFAULT_SEED
) -> Dict[str, Any]:
    """Generate deterministic 1D regression data: y = 0.5*x + 0.25*sin(3x) + noise."""
    n = int(n)
    seed = int(seed)
    if n <= 0:
        raise ValueError("n must be positive")
    if np is not None:
        rng = np.random.RandomState(seed)
        x = np.linspace(-3.0, 3.0, n, dtype=float)
        noise = rng.normal(loc=0.0, scale=0.15, size=n).astype(float)
        y = 0.5 * x + 0.25 * np.sin(3.0 * x) + noise
    else:
        rng = random.Random(seed)
        x = [(-3.0 + 6.0 * i / (n - 1 if n > 1 else 1)) for i in range(n)]
        noise = [rng.gauss(0.0, 0.15) for _ in range(n)]
        y = [0.5 * xi + 0.25 * math.sin(3.0 * xi) + ni for xi, ni in zip(x, noise)]
    dataset_id = _stable_hash(f"synthetic_regression|n={n}|seed={seed}")[:16]
    return {
        "schema_version": "1.0",
        "dataset": "synthetic_regression",
        "dataset_id": dataset_id,
        "n": n,
        "seed": seed,
        "x": _as_float_list(x),
        "y": _as_float_list(y),
    }


def fit_linear_model(x: Any, y: Any) -> Dict[str, Any]:
    """Deterministic ordinary least squares fit for y ~ a*x + b."""
    xs = _as_float_list(x)
    ys = _as_float_list(y)
    if len(xs) != len(ys) or len(xs) == 0:
        raise ValueError("x and y must be same non-empty length")
    n = float(len(xs))
    sx = sum(xs)
    sy = sum(ys)
    sxx = sum(v * v for v in xs)
    sxy = sum(a * b for a, b in zip(xs, ys))
    denom = (n * sxx - sx * sx)
    a = (n * sxy - sx * sy) / denom if denom != 0.0 else 0.0
    b = (sy - a * sx) / n
    yhat = [a * xi + b for xi in xs]
    return {"a": float(a), "b": float(b), "y_hat": yhat}


def compute_metrics(y_true: Any, y_pred: Any) -> Dict[str, Any]:
    yt = _as_float_list(y_true)
    yp = _as_float_list(y_pred)
    if len(yt) != len(yp) or len(yt) == 0:
        raise ValueError("y_true and y_pred must be same non-empty length")
    n = len(yt)
    err = [a - b for a, b in zip(yt, yp)]
    mse = sum(e * e for e in err) / n
    rmse = math.sqrt(mse)
    mae = sum(abs(e) for e in err) / n
    mean_y = sum(yt) / n
    ss_tot = sum((v - mean_y) ** 2 for v in yt)
    ss_res = sum(e * e for e in err)
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot != 0.0 else 0.0
    return {
        "n": int(n),
        "mse": float(mse),
        "rmse": float(rmse),
        "mae": float(mae),
        "r2": float(r2),
    }


def build_results(
    dataset: Dict[str, Any], model: Dict[str, Any], metrics: Dict[str, Any]
) -> Dict[str, Any]:
    """Assemble stable results dict for JSON serialization."""
    return {
        "schema_version": "1.0",
        "artifact": "results",
        "dataset": {
            "name": dataset.get("dataset"),
            "dataset_id": dataset.get("dataset_id"),
            "n": int(dataset.get("n")),
            "seed": int(dataset.get("seed")),
        },
        "model": {"type": "ols_linear", "a": float(model["a"]), "b": float(model["b"])},
        "metrics": metrics,
    }


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def run_core_workflow(
    seed: int = DEFAULT_SEED, n: int = 256
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Run deterministic data->fit->metrics; returns (dataset, results, model)."""
    set_global_determinism(seed)
    dataset = generate_synthetic_regression(n=n, seed=seed)
    model = fit_linear_model(dataset["x"], dataset["y"])
    metrics = compute_metrics(dataset["y"], model["y_hat"])
    results = build_results(dataset, model, metrics)
    return dataset, results, model
