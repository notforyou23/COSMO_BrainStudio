"""Plotting utilities for the meta-analysis starter-kit demo.

Primary deliverable: a saved forest plot written under outputs/figures/.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Union, Sequence

import numpy as np

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover
    pd = None  # type: ignore

import matplotlib
matplotlib.use("Agg", force=True)  # non-interactive backend for batch runs
import matplotlib.pyplot as plt
def _as_dataframe(studies: Union["pd.DataFrame", Sequence[Dict[str, Any]]]) -> "pd.DataFrame":
    if pd is None:
        raise ImportError("pandas is required for plotting (install pandas).")
    if isinstance(studies, pd.DataFrame):
        df = studies.copy()
    else:
        df = pd.DataFrame(list(studies))
    # Normalize common column names
    rename = {}
    if "effect" in df.columns and "yi" not in df.columns:
        rename["effect"] = "yi"
    if "se" in df.columns and "sei" not in df.columns:
        rename["se"] = "sei"
    if "study_id" in df.columns and "study" not in df.columns:
        rename["study_id"] = "study"
    if rename:
        df = df.rename(columns=rename)
    if "study" not in df.columns:
        df["study"] = [f"Study {i+1}" for i in range(len(df))]
    if "yi" not in df.columns:
        raise ValueError("studies must include an effect column: yi (or effect).")
    if "sei" not in df.columns:
        raise ValueError("studies must include a standard error column: sei (or se).")
    for c in ("yi", "sei"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    if df[["yi", "sei"]].isna().any().any():
        raise ValueError("studies contain non-numeric or missing yi/sei values.")
    if "ci_low" not in df.columns or "ci_high" not in df.columns:
        z = 1.96
        df["ci_low"] = df["yi"] - z * df["sei"]
        df["ci_high"] = df["yi"] + z * df["sei"]
    if "weight" in df.columns:
        df["weight"] = pd.to_numeric(df["weight"], errors="coerce")
    else:
        df["weight"] = 1.0 / np.maximum(df["sei"].to_numpy() ** 2, 1e-12)
    return df
def forest_plot(
    studies: Union["pd.DataFrame", Sequence[Dict[str, Any]]],
    pooled: Dict[str, Any],
    *,
    out_dir: Union[str, Path] = "outputs/figures",
    filename: str = "forest_plot.png",
    title: Optional[str] = None,
    effect_label: str = "Effect",
    subtitle: Optional[str] = None,
) -> Path:
    """Create and save a basic forest plot.

    Parameters
    ----------
    studies:
        Study-level results with columns: study, yi, sei, ci_low, ci_high, weight.
    pooled:
        Dict with keys: estimate (or yi), se (or sei), ci_low, ci_high, model (optional).
    out_dir:
        Output directory; created if missing.
    filename:
        Output filename (png).
    """
    df = _as_dataframe(studies)

    est = pooled.get("estimate", pooled.get("yi"))
    se = pooled.get("se", pooled.get("sei"))
    if est is None or se is None:
        raise ValueError("pooled must include estimate/yi and se/sei.")
    ci_low = pooled.get("ci_low", float(est) - 1.96 * float(se))
    ci_high = pooled.get("ci_high", float(est) + 1.96 * float(se))
    model = pooled.get("model", pooled.get("method", "pooled"))

    out_dir = Path(out_dir)
    if not out_dir.is_absolute():
        out_dir = Path("/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution").joinpath(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename

    n = len(df)
    y_studies = np.arange(n, 0, -1)  # top to bottom
    y_pooled = 0

    # Axis limits
    x_min = float(min(df["ci_low"].min(), ci_low))
    x_max = float(max(df["ci_high"].max(), ci_high))
    pad = 0.06 * (x_max - x_min if x_max > x_min else 1.0)
    xlim = (x_min - pad, x_max + pad)

    # Point sizes proportional to weights (clipped)
    w = df["weight"].to_numpy(dtype=float)
    w = np.clip(w, np.nanpercentile(w, 5), np.nanpercentile(w, 95))
    w = (w - w.min()) / (w.max() - w.min() + 1e-12)
    sizes = 20 + 140 * w

    fig_h = max(3.2, 0.34 * (n + 3))
    fig, ax = plt.subplots(figsize=(8.6, fig_h))

    # CIs and points for studies
    for i, row in enumerate(df.itertuples(index=False)):
        y = y_studies[i]
        ax.plot([row.ci_low, row.ci_high], [y, y], color="black", lw=1.2, solid_capstyle="butt")
        ax.scatter([row.yi], [y], s=float(sizes[i]), color="#1f77b4", edgecolor="black", linewidth=0.4, zorder=3)

    # Pooled diamond
    diamond_y = y_pooled
    mid = float(est)
    lo = float(ci_low)
    hi = float(ci_high)
    diamond = np.array([[lo, diamond_y], [mid, diamond_y + 0.28], [hi, diamond_y], [mid, diamond_y - 0.28]])
    ax.fill(diamond[:, 0], diamond[:, 1], color="#d62728", alpha=0.35, edgecolor="#d62728", linewidth=1.2, zorder=2)
    ax.plot([lo, hi], [diamond_y, diamond_y], color="#d62728", lw=1.2)

    # Reference line at 0
    ax.axvline(0.0, color="gray", lw=1.0, ls="--", alpha=0.8)

    # Y labels
    labels = list(df["study"].astype(str))
    ax.set_yticks(list(y_studies) + [y_pooled])
    ax.set_yticklabels(labels + [f"Pooled ({model})"])
    ax.set_ylim(-1, n + 1)
    ax.set_xlim(*xlim)
    ax.set_xlabel(effect_label)

    # Title/subtitle
    if title:
        ax.set_title(title, fontsize=12, pad=10)
    if subtitle:
        ax.text(0.0, 1.02, subtitle, transform=ax.transAxes, ha="left", va="bottom", fontsize=10)

    # Right-side numeric columns
    x_text = xlim[1]
    ax.text(x_text, n + 0.7, "Estimate [95% CI]", ha="right", va="bottom", fontsize=10, fontweight="bold")
    for i, row in enumerate(df.itertuples(index=False)):
        y = y_studies[i]
        s = f"{row.yi:.3f} [{row.ci_low:.3f}, {row.ci_high:.3f}]"
        ax.text(x_text, y, s, ha="right", va="center", fontsize=9)
    pooled_s = f"{mid:.3f} [{lo:.3f}, {hi:.3f}]"
    ax.text(x_text, y_pooled, pooled_s, ha="right", va="center", fontsize=9, fontweight="bold")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out_path
