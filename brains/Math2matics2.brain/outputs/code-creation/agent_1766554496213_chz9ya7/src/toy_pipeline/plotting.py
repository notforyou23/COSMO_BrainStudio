"""Plotting utilities for the toy pipeline.

The functions here are designed to be reproducible: fixed styling, fixed
figure size/dpi, and a non-interactive backend.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import numpy as np
def _as_1d(x: Any) -> np.ndarray:
    """Convert a sequence/array-like to a 1D float numpy array."""
    if x is None:
        return np.asarray([], dtype=float)
    arr = np.asarray(x, dtype=float)
    return arr.reshape(-1)
def apply_reproducible_style() -> None:
    """Apply deterministic matplotlib styling (idempotent)."""
    plt.rcParams.update(
        {
            "figure.figsize": (8.0, 5.0),
            "figure.dpi": 120,
            "savefig.dpi": 120,
            "font.size": 10.0,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.titlepad": 8.0,
            "legend.frameon": False,
            "lines.linewidth": 1.5,
            "lines.markersize": 4.0,
            "image.interpolation": "nearest",
        }
    )
def plot_experiment_results(
    results: Mapping[str, Any],
    out_png: str | Path,
    *,
    title: str = "Toy pipeline results",
) -> Path:
    """Create and save a reproducible PNG summarizing experiment results.

    Expected keys in `results` (if present):
      - y_true: sequence[float]
      - y_pred: sequence[float]
      - train_losses: sequence[float]
    """
    apply_reproducible_style()

    out_path = Path(out_png)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    y_true = _as_1d(results.get("y_true"))
    y_pred = _as_1d(results.get("y_pred"))
    losses = _as_1d(results.get("train_losses"))

    n = int(min(y_true.size, y_pred.size))
    y_true = y_true[:n]
    y_pred = y_pred[:n]
    resid = (y_pred - y_true) if n else np.asarray([], dtype=float)

    fig, axes = plt.subplots(2, 2, figsize=(8.0, 5.0), dpi=120)
    ax_scatter, ax_resid, ax_loss, ax_text = axes.ravel()

    # Scatter: predictions vs truth
    if n:
        ax_scatter.scatter(y_true, y_pred, s=18, alpha=0.9, edgecolors="none")
        lo = float(min(y_true.min(), y_pred.min()))
        hi = float(max(y_true.max(), y_pred.max()))
        pad = (hi - lo) * 0.05 if hi > lo else 1.0
        lo -= pad
        hi += pad
        ax_scatter.plot([lo, hi], [lo, hi], color="black", alpha=0.6, linewidth=1.0)
        ax_scatter.set_xlim(lo, hi)
        ax_scatter.set_ylim(lo, hi)
    ax_scatter.set_title("Predicted vs. true")
    ax_scatter.set_xlabel("y_true")
    ax_scatter.set_ylabel("y_pred")

    # Residuals histogram
    if resid.size:
        bins = 21
        ax_resid.hist(resid, bins=bins, color="#4C72B0", alpha=0.9)
        ax_resid.axvline(0.0, color="black", alpha=0.6, linewidth=1.0)
    ax_resid.set_title("Residuals (y_pred - y_true)")
    ax_resid.set_xlabel("residual")
    ax_resid.set_ylabel("count")

    # Loss curve
    if losses.size:
        ax_loss.plot(np.arange(losses.size), losses, marker="o")
        ax_loss.set_xlim(0, max(0, losses.size - 1))
    ax_loss.set_title("Training loss")
    ax_loss.set_xlabel("epoch")
    ax_loss.set_ylabel("loss")

    # Text summary
    ax_text.axis("off")
    lines: list[str] = [title]
    metrics = results.get("metrics", {})
    if isinstance(metrics, Mapping) and metrics:
        for k in sorted(metrics.keys()):
            v = metrics[k]
            if isinstance(v, (int, float, np.floating)):
                lines.append(f"{k}: {float(v):.6g}")
            else:
                lines.append(f"{k}: {v}")
    else:
        if n:
            mse = float(np.mean((y_pred - y_true) ** 2))
            mae = float(np.mean(np.abs(y_pred - y_true)))
            lines.extend([f"mse: {mse:.6g}", f"mae: {mae:.6g}", f"n: {n}"])
        else:
            lines.append("No data provided.")
    ax_text.text(0.0, 1.0, "\n".join(lines), va="top", ha="left")

    fig.suptitle(title)
    fig.tight_layout(rect=(0, 0, 1, 0.94))

    # Keep output stable by setting minimal metadata (avoid timestamps when possible).
    fig.savefig(
        out_path,
        format="png",
        facecolor="white",
        edgecolor="none",
        metadata={"Software": "toy_pipeline"},
        pil_kwargs={"compress_level": 9},
    )
    plt.close(fig)
    return out_path
