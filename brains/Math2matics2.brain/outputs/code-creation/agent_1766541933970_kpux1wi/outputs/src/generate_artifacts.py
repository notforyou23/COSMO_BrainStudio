#!/usr/bin/env python3
"""Deterministically generate small artifacts into outputs/.

Creates:
- outputs/synthetic_results.json (summary stats + run metadata)
- outputs/synthetic_plot.png (plot of the synthetic data)
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
def _stable_run_id(payload: dict) -> str:
    """Deterministic ID derived from the configuration payload."""
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]
def main() -> int:
    # Layout: outputs/src/generate_artifacts.py -> outputs/
    outputs_dir = Path(__file__).resolve().parents[1]
    outputs_dir.mkdir(parents=True, exist_ok=True)

    cfg = {
        "seed": 12345,
        "n": 200,
        "noise_std": 0.15,
        "x_min": 0.0,
        "x_max": 8.0 * np.pi,
    }
    run_id = _stable_run_id(cfg)

    rng = np.random.default_rng(cfg["seed"])
    x = np.linspace(cfg["x_min"], cfg["x_max"], cfg["n"])
    y_true = np.sin(x) + 0.2 * np.cos(2.0 * x)
    y = y_true + rng.normal(0.0, cfg["noise_std"], size=cfg["n"])

    residual = y - y_true
    stats = {
        "n": int(cfg["n"]),
        "x_mean": float(np.mean(x)),
        "x_std": float(np.std(x, ddof=1)),
        "y_mean": float(np.mean(y)),
        "y_std": float(np.std(y, ddof=1)),
        "rmse_vs_true": float(np.sqrt(np.mean(residual**2))),
        "corr_x_y": float(np.corrcoef(x, y)[0, 1]),
        "y_min": float(np.min(y)),
        "y_max": float(np.max(y)),
    }

    # Deterministic plot styling
    fig, ax = plt.subplots(figsize=(7.2, 4.0), dpi=120)
    ax.plot(x, y_true, color="black", linewidth=2.0, label="true signal")
    ax.scatter(x, y, s=12, alpha=0.65, label="observed (noisy)")
    ax.set_title("Deterministic synthetic dataset")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.grid(True, linestyle="--", linewidth=0.6, alpha=0.5)
    ax.legend(loc="best", frameon=True)
    fig.tight_layout()

    png_path = outputs_dir / "synthetic_plot.png"
    fig.savefig(png_path)
    plt.close(fig)

    results = {
        "run_id": run_id,
        "config": {
            "seed": int(cfg["seed"]),
            "n": int(cfg["n"]),
            "noise_std": float(cfg["noise_std"]),
            "x_min": float(cfg["x_min"]),
            "x_max": float(cfg["x_max"]),
        },
        "summary_stats": stats,
        "artifacts": {
            "plot_png": png_path.name,
            "results_json": "synthetic_results.json",
        },
    }

    json_path = outputs_dir / "synthetic_results.json"
    json_path.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Minimal deterministic console status
    print(f"WROTE:{png_path.relative_to(outputs_dir)}")
    print(f"WROTE:{json_path.relative_to(outputs_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
