#!/usr/bin/env python3
\"\"\"Seeded toy experiment that writes deterministic artifacts.

Produces:
- results.json: summary statistics + metadata (deterministic for same inputs)
- figure.png: simple deterministic plot of the generated data

Usage:
  python -m src.goal_33_toy_experiment --outdir . --seed 0 --n 1000
\"\"\"
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path
from typing import Any, Dict

import numpy as np

# Use a non-interactive backend for CI/headless environments.
import matplotlib
matplotlib.use("Agg")  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
def _stable_sha256(obj: Any) -> str:
    \"\"\"SHA256 of a JSON-serializable object with stable encoding.\"\"\"
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def run_experiment(seed: int, n: int) -> Dict[str, Any]:
    rng = np.random.default_rng(seed)

    # Deterministic toy signal: Gaussian noise + a smooth sinusoid trend.
    x = np.linspace(0.0, 1.0, n, dtype=np.float64)
    noise = rng.normal(loc=0.0, scale=1.0, size=n).astype(np.float64)
    y = noise + 0.25 * np.sin(2.0 * np.pi * 3.0 * x)

    stats = {
        "n": int(n),
        "seed": int(seed),
        "mean": float(np.mean(y)),
        "std": float(np.std(y, ddof=1)),
        "min": float(np.min(y)),
        "max": float(np.max(y)),
        "q25": float(np.quantile(y, 0.25)),
        "q50": float(np.quantile(y, 0.50)),
        "q75": float(np.quantile(y, 0.75)),
    }

    # Stable checksum derived from rounded values serialized as JSON.
    rounded = np.round(y, 8).tolist()
    stats["data_sha256"] = _stable_sha256(rounded)

    meta = {
        "experiment": "goal_33_toy_experiment",
        "schema_version": 1,
        "inputs": {"seed": int(seed), "n": int(n)},
        "python": platform.python_version(),
        "numpy": np.__version__,
        "matplotlib": matplotlib.__version__,
    }
    meta["run_sha256"] = _stable_sha256({"meta": meta, "stats": stats})
    return {"metadata": meta, "stats": stats, "rounded_sample_head": rounded[:10]}
def write_artifacts(result: Dict[str, Any], outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    results_path = outdir / "results.json"
    fig_path = outdir / "figure.png"

    results_path.write_text(
        json.dumps(result, sort_keys=True, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    # Deterministic plot: empirical CDF of y using sorted rounded values.
    y = np.array(result["rounded_sample_head"] + [])  # just to keep type consistent
    # Rebuild a deterministic view of data via checksum context is not needed for plot;
    # instead, re-run plotting from summary-friendly data: use quantile markers.
    # Plot a simple bar of key quantiles and mean to keep it deterministic.
    stats = result["stats"]
    labels = ["min", "q25", "q50", "mean", "q75", "max"]
    values = [stats["min"], stats["q25"], stats["q50"], stats["mean"], stats["q75"], stats["max"]]

    plt.rcParams.update({"figure.dpi": 120, "savefig.dpi": 120})
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.plot(labels, values, marker="o", linewidth=2)
    ax.set_title("Toy experiment summary (deterministic)")
    ax.set_ylabel("value")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(fig_path)
    plt.close(fig)
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Goal 33: deterministic toy experiment")
    p.add_argument("--outdir", type=Path, default=Path("."), help="Output directory")
    p.add_argument("--seed", type=int, default=0, help="Random seed")
    p.add_argument("--n", type=int, default=1000, help="Number of samples")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.n <= 1:
        raise SystemExit("--n must be > 1")
    result = run_experiment(seed=args.seed, n=args.n)
    write_artifacts(result, args.outdir)
    print(f"WROTE:{(args.outdir / 'results.json').as_posix()}")
    print(f"WROTE:{(args.outdir / 'figure.png').as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
