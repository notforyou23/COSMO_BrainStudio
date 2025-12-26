"""Plotting utilities.

Designed for publication-ready figures used across the project:
- hypothesis rankings
- constraint projections / forecasts
- posterior summaries
- robustness diagnostics

All functions return (fig, ax) and can optionally save to disk.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

import numpy as np
def _lazy_import_mpl():
    import matplotlib as mpl  # noqa: WPS433
    import matplotlib.pyplot as plt  # noqa: WPS433
    return mpl, plt


def set_mpl_style(
    *,
    base: str = "seaborn-v0_8-whitegrid",
    fontsize: int = 10,
    linewidth: float = 1.2,
) -> None:
    """Set a clean, consistent matplotlib style (idempotent)."""
    mpl, _ = _lazy_import_mpl()
    try:
        mpl.style.use(base)
    except Exception:
        pass
    mpl.rcParams.update(
        {
            "font.size": fontsize,
            "axes.labelsize": fontsize,
            "axes.titlesize": fontsize + 1,
            "legend.fontsize": fontsize - 1,
            "xtick.labelsize": fontsize - 1,
            "ytick.labelsize": fontsize - 1,
            "axes.linewidth": linewidth,
            "grid.alpha": 0.35,
            "figure.dpi": 120,
            "savefig.bbox": "tight",
            "savefig.transparent": False,
        }
    )


def savefig(fig, path: Union[str, Path], *, dpi: int = 300) -> Path:
    """Save figure to *path* (creating parents). Returns resolved Path."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=dpi)
    return out.resolve()
@dataclass(frozen=True)
class Band:
    ymin: float
    ymax: float
    label: str = ""
    color: str = "C0"
    alpha: float = 0.12


def plot_hypothesis_ranking(
    table: Any,
    *,
    label_col: str = "hypothesis",
    score_col: str = "score",
    err_col: Optional[str] = None,
    top_n: int = 15,
    title: str = "Hypothesis ranking",
    xlabel: str = "Score",
    color: str = "C0",
    figsize: Tuple[float, float] = (6.2, 4.0),
    save_to: Optional[Union[str, Path]] = None,
):
    """Horizontal bar ranking with optional uncertainty (err_col)."""
    mpl, plt = _lazy_import_mpl()
    set_mpl_style()

    df = table.copy() if hasattr(table, "copy") else table
    df = df.sort_values(score_col, ascending=True).tail(top_n)
    labels = df[label_col].astype(str).to_numpy()
    scores = df[score_col].to_numpy()
    errs = df[err_col].to_numpy() if err_col and err_col in df.columns else None

    fig, ax = plt.subplots(figsize=figsize)
    y = np.arange(len(labels))
    ax.barh(y, scores, xerr=errs, color=color, alpha=0.9, ecolor="0.2", capsize=2)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    ax.axvline(0.0, color="0.3", lw=1.0)
    ax.margins(y=0.02)

    if save_to is not None:
        savefig(fig, save_to)
    return fig, ax
def plot_constraint_projection(
    x: Sequence[float],
    y: Sequence[float],
    *,
    yerr: Optional[Sequence[float]] = None,
    bands: Optional[Sequence[Band]] = None,
    xlabel: str = "Model parameter",
    ylabel: str = "Observable",
    title: str = "Constraint projection",
    label: str = "prediction",
    color: str = "C0",
    figsize: Tuple[float, float] = (6.2, 4.0),
    save_to: Optional[Union[str, Path]] = None,
):
    """Line/points with error bars and optional horizontal allowed bands."""
    _, plt = _lazy_import_mpl()
    set_mpl_style()

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    yerr_arr = None if yerr is None else np.asarray(yerr, dtype=float)

    fig, ax = plt.subplots(figsize=figsize)
    if bands:
        for b in bands:
            ax.axhspan(b.ymin, b.ymax, color=b.color, alpha=b.alpha, label=b.label or None)

    if yerr_arr is None:
        ax.plot(x, y, color=color, lw=2.0, label=label)
    else:
        ax.errorbar(x, y, yerr=yerr_arr, fmt="o-", color=color, lw=1.6, ms=3.5, capsize=2, label=label)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    if bands or label:
        ax.legend(frameon=True, loc="best")
    ax.grid(True, which="both")
    if save_to is not None:
        savefig(fig, save_to)
    return fig, ax
def _credible_interval(a: np.ndarray, q: Tuple[float, float] = (0.16, 0.84)) -> Tuple[float, float, float]:
    a = np.asarray(a, dtype=float)
    a = a[np.isfinite(a)]
    if a.size == 0:
        return np.nan, np.nan, np.nan
    lo, med, hi = np.quantile(a, [q[0], 0.5, q[1]])
    return float(lo), float(med), float(hi)


def plot_posterior_summary(
    samples: Mapping[str, Sequence[float]],
    *,
    truths: Optional[Mapping[str, float]] = None,
    q: Tuple[float, float] = (0.16, 0.84),
    title: str = "Posterior summary",
    xlabel: str = "Parameter",
    ylabel: str = "Value",
    color: str = "C0",
    figsize: Tuple[float, float] = (6.2, 4.0),
    save_to: Optional[Union[str, Path]] = None,
):
    """Compact 1D posterior summary (median + credible intervals per parameter)."""
    _, plt = _lazy_import_mpl()
    set_mpl_style()

    names = list(samples.keys())
    stats = [_credible_interval(np.asarray(samples[n]), q=q) for n in names]
    lo = np.array([s[0] for s in stats])
    med = np.array([s[1] for s in stats])
    hi = np.array([s[2] for s in stats])

    fig, ax = plt.subplots(figsize=figsize)
    x = np.arange(len(names))
    ax.vlines(x, lo, hi, color=color, lw=2.0, alpha=0.9)
    ax.scatter(x, med, color=color, s=22, zorder=3, label="median")
    if truths:
        t = np.array([truths.get(n, np.nan) for n in names], dtype=float)
        ax.scatter(x, t, color="C3", s=18, marker="x", zorder=4, label="truth")

    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=30, ha="right")
    ax.set_ylabel(ylabel)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    ax.legend(frameon=True, loc="best")
    ax.margins(x=0.02)
    if save_to is not None:
        savefig(fig, save_to)
    return fig, ax
def plot_robustness_diagnostics(
    table: Any,
    *,
    variant_col: str = "variant",
    metric_col: str = "metric",
    value_col: str = "value",
    title: str = "Robustness diagnostics",
    ylabel: str = "Metric value",
    figsize: Tuple[float, float] = (7.0, 4.0),
    save_to: Optional[Union[str, Path]] = None,
):
    """Box/strip plot of metric values across compactification/flux variants."""
    _, plt = _lazy_import_mpl()
    set_mpl_style()

    df = table.copy() if hasattr(table, "copy") else table
    metrics = df[metric_col].astype(str).unique().tolist()
    variants = df[variant_col].astype(str).unique().tolist()

    fig, ax = plt.subplots(figsize=figsize)
    positions, labels = [], []
    pos = 0
    for m in metrics:
        for v in variants:
            vals = df[(df[metric_col] == m) & (df[variant_col] == v)][value_col].to_numpy(dtype=float)
            if vals.size == 0:
                continue
            positions.append(pos)
            labels.append(f"{m}\n{v}")
            ax.boxplot(vals, positions=[pos], widths=0.6, showfliers=False, patch_artist=True,
                       boxprops=dict(facecolor="0.85", edgecolor="0.3"),
                       medianprops=dict(color="C0", linewidth=1.6),
                       whiskerprops=dict(color="0.3"), capprops=dict(color="0.3"))
            jitter = (np.random.RandomState(0).rand(vals.size) - 0.5) * 0.18
            ax.scatter(np.full(vals.size, pos) + jitter, vals, s=10, color="0.25", alpha=0.6, zorder=3)
            pos += 1
        pos += 0.6  # gap between metrics

    ax.set_xticks(positions)
    ax.set_xticklabels(labels, rotation=0)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, axis="y")
    if save_to is not None:
        savefig(fig, save_to)
    return fig, ax
