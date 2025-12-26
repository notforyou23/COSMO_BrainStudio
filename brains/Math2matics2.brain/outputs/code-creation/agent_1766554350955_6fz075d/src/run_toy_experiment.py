#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

DEFAULT_CONTRACT_VERSION = "1.0"
WORKDIR = Path("/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution")
OUTPUTS_DIR = WORKDIR / "outputs"
RESULTS_PATH = OUTPUTS_DIR / "results.json"
FIG_PATH = OUTPUTS_DIR / "figure.png"


def seed_all(seed: int) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
def sample_heavy_tailed_t(rng: np.random.RandomState, n: int, df: float, loc: float = 0.0, scale: float = 1.0) -> np.ndarray:
    x = rng.standard_t(df, size=n)
    return loc + scale * x


def sample_mean(x: np.ndarray) -> float:
    return float(np.mean(x))


def median_of_means(x: np.ndarray, groups: int) -> float:
    if groups < 1:
        raise ValueError("groups must be >= 1")
    n = int(x.shape[0])
    g = min(groups, n)
    splits = np.array_split(x, g)
    means = np.array([np.mean(s) for s in splits], dtype=float)
    return float(np.median(means))


def summarize_errors(errors: np.ndarray) -> dict:
    ae = np.abs(errors)
    return {
        "rmse": float(np.sqrt(np.mean(errors ** 2))),
        "mae": float(np.mean(ae)),
        "median_abs_error": float(np.median(ae)),
    }


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
def make_figure(errors: dict[str, np.ndarray], out_path: Path, bins: int = 30) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "figure.dpi": 120,
        "savefig.dpi": 120,
        "font.size": 10,
        "axes.grid": True,
        "axes.linewidth": 0.8,
        "grid.linewidth": 0.6,
        "grid.alpha": 0.5,
        "lines.linewidth": 1.4,
        "patch.edgecolor": "black",
        "patch.linewidth": 0.6,
    })

    labels = list(errors.keys())
    data = [np.abs(errors[k]) for k in labels]
    vmax = float(np.max([np.max(d) for d in data])) if data else 1.0
    xmax = max(1e-9, min(vmax, np.quantile(np.concatenate(data), 0.99) if data else 1.0))

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for k, d in zip(labels, data):
        ax.hist(d, bins=bins, range=(0.0, xmax), density=True, alpha=0.45, label=k)
    ax.set_title("Absolute error distribution (heavy-tailed t)")
    ax.set_xlabel("|estimate - true_mean|")
    ax.set_ylabel("Density")
    ax.legend(frameon=True, loc="upper right")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
def validate_contract(d: dict) -> None:
    req_top = ["contract_version", "generated_at_utc", "seed", "paths", "experiment", "estimators", "metrics"]
    for k in req_top:
        if k not in d:
            raise ValueError(f"missing key: {k}")
    if not isinstance(d["contract_version"], str):
        raise TypeError("contract_version must be str")
    if not isinstance(d["seed"], int):
        raise TypeError("seed must be int")
    if not isinstance(d["paths"], dict) or "results_json" not in d["paths"] or "figure_png" not in d["paths"]:
        raise TypeError("paths must be dict with results_json and figure_png")
    if not isinstance(d["experiment"], dict):
        raise TypeError("experiment must be dict")
    if not isinstance(d["estimators"], list) or not all(isinstance(x, str) for x in d["estimators"]):
        raise TypeError("estimators must be list[str]")
    if not isinstance(d["metrics"], dict):
        raise TypeError("metrics must be dict")


def run(seed: int, n: int, trials: int, df: float, mom_groups: int) -> dict:
    seed_all(seed)
    rng = np.random.RandomState(seed)

    true_mean = 0.0
    errs = {"sample_mean": np.empty(trials, dtype=float), "median_of_means": np.empty(trials, dtype=float)}
    for t in range(trials):
        x = sample_heavy_tailed_t(rng, n=n, df=df, loc=0.0, scale=1.0)
        errs["sample_mean"][t] = sample_mean(x) - true_mean
        errs["median_of_means"][t] = median_of_means(x, groups=mom_groups) - true_mean

    metrics = {k: summarize_errors(v) for k, v in errs.items()}
    return {
        "true_mean": true_mean,
        "errors": {k: v.tolist() for k, v in errs.items()},
        "metrics": metrics,
    }
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Deterministic heavy-tailed toy experiment: sample mean vs median-of-means.")
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--n", type=int, default=256, help="samples per trial")
    ap.add_argument("--trials", type=int, default=400, help="number of Monte Carlo trials")
    ap.add_argument("--df", type=float, default=2.0, help="degrees of freedom for Student-t (heavy-tailed for small df)")
    ap.add_argument("--mom-groups", type=int, default=16, help="number of groups for median-of-means")
    ap.add_argument("--bins", type=int, default=30, help="histogram bins for figure")
    args = ap.parse_args(argv)

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    run_out = run(seed=args.seed, n=args.n, trials=args.trials, df=args.df, mom_groups=args.mom_groups)
    make_figure({k: np.array(v, dtype=float) for k, v in run_out["errors"].items()}, FIG_PATH, bins=args.bins)

    result = {
        "contract_version": DEFAULT_CONTRACT_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "seed": int(args.seed),
        "paths": {
            "results_json": str(RESULTS_PATH),
            "figure_png": str(FIG_PATH),
        },
        "experiment": {
            "name": "heavy_tailed_mean_vs_mom",
            "distribution": "student_t",
            "df": float(args.df),
            "n": int(args.n),
            "trials": int(args.trials),
            "mom_groups": int(args.mom_groups),
            "true_mean": float(run_out["true_mean"]),
        },
        "estimators": ["sample_mean", "median_of_means"],
        "metrics": run_out["metrics"],
        "errors": run_out["errors"],
        "artifacts": {
            "figure_sha256": sha256_file(FIG_PATH),
        },
    }
    validate_contract(result)
    RESULTS_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
