#!/usr/bin/env python3
\"\"\"Deterministic, seed-controlled toy experiment.

This script generates synthetic linear data, fits a least-squares model, and
writes two artifacts for test validation:

- <output_dir>/results.json
- <output_dir>/figure.png
\"\"\"
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, Tuple

import numpy as np
def _seed_everything(seed: int) -> np.random.Generator:
    # Ensure deterministic hash-based operations when this process spawns libs.
    os.environ.setdefault("PYTHONHASHSEED", str(seed))
    return np.random.default_rng(seed)
def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path
def _stable_json_dump(data: Dict[str, Any], path: Path) -> None:
    def _coerce(obj: Any) -> Any:
        if isinstance(obj, (np.floating,)):
            return float(np.round(obj, 12))
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, np.ndarray):
            return [_coerce(x) for x in obj.tolist()]
        if isinstance(obj, dict):
            return {str(k): _coerce(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_coerce(x) for x in obj]
        return obj

    coerced = _coerce(data)
    text = json.dumps(coerced, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")
def _make_dataset(
    rng: np.random.Generator, n: int, noise: float
) -> Tuple[np.ndarray, np.ndarray, Dict[str, float]]:
    x = rng.uniform(-2.0, 2.0, size=n)
    true_w = 1.75
    true_b = -0.4
    y = true_w * x + true_b + rng.normal(0.0, noise, size=n)
    return x, y, {"w": true_w, "b": true_b}
def _fit_least_squares(x: np.ndarray, y: np.ndarray) -> Dict[str, float]:
    # Solve for [w, b] in y ≈ w*x + b using normal equations.
    X = np.column_stack([x, np.ones_like(x)])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    w_hat, b_hat = beta
    return {"w": float(w_hat), "b": float(b_hat)}
def _metrics(x: np.ndarray, y: np.ndarray, params: Dict[str, float]) -> Dict[str, float]:
    y_hat = params["w"] * x + params["b"]
    resid = y - y_hat
    mse = float(np.mean(resid**2))
    ss_tot = float(np.sum((y - float(np.mean(y))) ** 2))
    ss_res = float(np.sum(resid**2))
    r2 = 1.0 - (ss_res / ss_tot if ss_tot > 0 else 0.0)
    return {"mse": mse, "r2": float(r2)}
def _save_figure(x: np.ndarray, y: np.ndarray, params: Dict[str, float], out_path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 4), dpi=150)
    ax.scatter(x, y, s=10, alpha=0.85, edgecolor="none")
    xs = np.linspace(float(np.min(x)), float(np.max(x)), 200)
    ax.plot(xs, params["w"] * xs + params["b"], linewidth=2)
    ax.set_title("Toy linear regression (deterministic)")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_path, format="png")
    plt.close(fig)
def run(seed: int, n: int, noise: float, output_dir: Path) -> Dict[str, Any]:
    rng = _seed_everything(seed)
    x, y, true_params = _make_dataset(rng, n=n, noise=noise)
    est_params = _fit_least_squares(x, y)
    mets = _metrics(x, y, est_params)

    out_dir = _ensure_dir(output_dir)
    results_path = out_dir / "results.json"
    fig_path = out_dir / "figure.png"

    results: Dict[str, Any] = {
        "seed": int(seed),
        "n": int(n),
        "noise": float(noise),
        "true_params": true_params,
        "estimated_params": est_params,
        "metrics": mets,
        # A tiny checksum-like summary for tests.
        "y_mean": float(np.mean(y)),
        "y_std": float(np.std(y)),
    }
    _stable_json_dump(results, results_path)
    _save_figure(x, y, est_params, fig_path)
    return results
def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run a deterministic toy experiment.")
    p.add_argument("--seed", type=int, default=0, help="RNG seed (default: 0)")
    p.add_argument("--n", type=int, default=200, help="Number of samples (default: 200)")
    p.add_argument("--noise", type=float, default=0.25, help="Gaussian noise std (default: 0.25)")
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="Output directory (default: ./outputs)",
    )
    return p.parse_args(argv)
def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    run(seed=args.seed, n=args.n, noise=args.noise, output_dir=args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
