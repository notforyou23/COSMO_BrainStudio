#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


SCHEMA_VERSION = "toy_experiment.v1"


def seed_all(seed: int) -> np.random.Generator:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    return np.random.default_rng(seed)


def sample_mean(x: np.ndarray) -> float:
    return float(np.mean(x))


def median_of_means(x: np.ndarray, k: int) -> float:
    n = int(x.shape[0])
    k = max(1, int(k))
    b = max(1, n // k)
    m = b * k
    x2 = x[:m]
    means = np.mean(x2.reshape(k, b), axis=1)
    return float(np.median(means))


def summarize_errors(err: np.ndarray) -> Dict[str, float]:
    ae = np.abs(err)
    return {
        "mae": float(np.mean(ae)),
        "rmse": float(np.sqrt(np.mean(err * err))),
        "median_abs_error": float(np.median(ae)),
        "p95_abs_error": float(np.quantile(ae, 0.95)),
    }


def validate_contract(d: Dict[str, Any]) -> None:
    req_top = ["schema_version", "created_utc", "seed", "params", "metrics", "artifacts"]
    for k in req_top:
        if k not in d:
            raise ValueError(f"Missing top-level key: {k}")
    if d["schema_version"] != SCHEMA_VERSION:
        raise ValueError("schema_version mismatch")
    if not isinstance(d["seed"], int):
        raise ValueError("seed must be int")
    for est in ["sample_mean", "median_of_means"]:
        if est not in d["metrics"]:
            raise ValueError(f"Missing metrics for {est}")
        for mk in ["mae", "rmse", "median_abs_error", "p95_abs_error"]:
            if mk not in d["metrics"][est]:
                raise ValueError(f"Missing metric {mk} for {est}")


def make_figure(abs_err_mean: np.ndarray, abs_err_mom: np.ndarray, out_path: Path) -> None:
    plt.rcParams.update({
        "figure.dpi": 100,
        "savefig.dpi": 100,
        "font.family": "DejaVu Sans",
        "axes.grid": True,
        "grid.alpha": 0.3,
    })
    fig, ax = plt.subplots(figsize=(8, 4))
    bins = np.linspace(0.0, float(max(abs_err_mean.max(), abs_err_mom.max())), 41)
    ax.hist(abs_err_mean, bins=bins, alpha=0.60, label="Sample mean", color="#1f77b4", density=True)
    ax.hist(abs_err_mom, bins=bins, alpha=0.60, label="Median-of-means", color="#ff7f0e", density=True)
    ax.set_title("Heavy-tailed toy experiment: absolute error distribution")
    ax.set_xlabel("Absolute error")
    ax.set_ylabel("Density")
    ax.legend(frameon=False)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)


def main() -> int:
    p = argparse.ArgumentParser(description="Deterministic heavy-tailed toy experiment (mean vs median-of-means).")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--n", type=int, default=200, help="samples per trial")
    p.add_argument("--trials", type=int, default=2000)
    p.add_argument("--k", type=int, default=10, help="number of blocks for median-of-means")
    p.add_argument("--df", type=float, default=2.5, help="degrees of freedom for Student-t (heavy-tailed)")
    args = p.parse_args()

    rng = seed_all(args.seed)

    true_mean = 0.0
    err_mean = np.empty(args.trials, dtype=np.float64)
    err_mom = np.empty(args.trials, dtype=np.float64)

    for t in range(args.trials):
        x = rng.standard_t(df=args.df, size=args.n)
        err_mean[t] = sample_mean(x) - true_mean
        err_mom[t] = median_of_means(x, k=args.k) - true_mean

    metrics = {
        "sample_mean": summarize_errors(err_mean),
        "median_of_means": summarize_errors(err_mom),
    }

    root = Path(__file__).resolve().parents[1]
    out_dir = root / "outputs"
    results_path = out_dir / "results.json"
    fig_path = out_dir / "figure.png"

    payload: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "seed": int(args.seed),
        "params": {
            "distribution": {"name": "student_t", "df": float(args.df), "true_mean": float(true_mean)},
            "n": int(args.n),
            "trials": int(args.trials),
            "median_of_means_blocks_k": int(args.k),
        },
        "metrics": metrics,
        "artifacts": {
            "results_json": str(results_path.relative_to(root)),
            "figure_png": str(fig_path.relative_to(root)),
        },
    }

    validate_contract(payload)
    out_dir.mkdir(parents=True, exist_ok=True)
    results_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    make_figure(np.abs(err_mean), np.abs(err_mom), fig_path)

    print(f"WROTE {results_path} and {fig_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
