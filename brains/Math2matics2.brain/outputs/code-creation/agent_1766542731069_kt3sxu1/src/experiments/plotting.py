"""Plotting utilities for sweep results.

The functions in this module are intentionally small and side-effect minimal:
they *return* matplotlib Figure/Axes objects and never call ``plt.show()``.
Inputs are standard-library friendly (list-of-dicts rows as produced by
:func:`experiments.io.read_results_csv`).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, Tuple, List, Optional, Dict

from ._common import as_path, ensure_parent_dir, ensure_suffix, require, check_one_of

__all__ = [
    "summarize_metrics",
    "plot_metric_vs_param",
    "plot_metrics_grid",
    "plot_summary_bars",
    "save_figure",
]
def _mpl():
    """Import matplotlib lazily with a clear error if unavailable."""
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "matplotlib is required for plotting utilities; install it to use experiments.plotting"
        ) from e
    return plt


def _to_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(x)
    except Exception:
        return None
def summarize_metrics(
    rows: Sequence[Mapping[str, Any]],
    metrics: Sequence[str],
    *,
    group_by: str | None = None,
) -> Dict[str, Dict[str, float]]:
    """Summarize numeric metrics across *rows*.

    Returns a nested dict: ``{metric: {count, mean, min, max}}``.
    If ``group_by`` is provided, that key must exist in each row; its value is
    ignored here (use it for consistency checks before plotting).
    """
    out: Dict[str, Dict[str, float]] = {}
    if group_by is not None:
        for r in rows:
            require(group_by in r, f"Missing group_by key {group_by!r} in a results row")
    for m in metrics:
        vals = [_to_float(r.get(m)) for r in rows]
        nums = [v for v in vals if v is not None]
        if not nums:
            out[m] = {"count": 0.0, "mean": float("nan"), "min": float("nan"), "max": float("nan")}
            continue
        out[m] = {
            "count": float(len(nums)),
            "mean": float(sum(nums) / len(nums)),
            "min": float(min(nums)),
            "max": float(max(nums)),
        }
    return out
def plot_metric_vs_param(
    rows: Sequence[Mapping[str, Any]],
    *,
    param: str,
    metric: str,
    agg: str = "mean",
    ax=None,
    sort_x: bool = True,
    label: str | None = None,
):
    """Plot *metric* as a function of *param*.

    Aggregates repeated param values using ``agg`` in {mean,min,max,median}.
    Returns ``(fig, ax)``.
    """
    agg = check_one_of("agg", agg, ("mean", "min", "max", "median"))
    xs: Dict[float, List[float]] = {}
    for r in rows:
        x = _to_float(r.get(param))
        y = _to_float(r.get(metric))
        if x is None or y is None:
            continue
        xs.setdefault(x, []).append(y)
    require(xs, f"No numeric data found for param={param!r} metric={metric!r}")
    def _reduce(vs: List[float]) -> float:
        if agg == "mean":
            return sum(vs) / len(vs)
        if agg == "min":
            return min(vs)
        if agg == "max":
            return max(vs)
        return float(sorted(vs)[len(vs)//2])
    xvals = list(xs.keys())
    if sort_x:
        xvals.sort()
    yvals = [_reduce(xs[x]) for x in xvals]
    plt = _mpl()
    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure
    ax.plot(xvals, yvals, marker="o", label=label or metric)
    ax.set_xlabel(param)
    ax.set_ylabel(metric)
    if label is not None:
        ax.legend()
    ax.grid(True, alpha=0.3)
    return fig, ax
def plot_metrics_grid(
    rows: Sequence[Mapping[str, Any]],
    *,
    param: str,
    metrics: Sequence[str],
    agg: str = "mean",
    ncols: int = 2,
    figsize: Tuple[float, float] | None = None,
):
    """Create a grid of ``plot_metric_vs_param`` for multiple *metrics*."""
    require(ncols >= 1, "ncols must be >= 1")
    plt = _mpl()
    n = len(metrics)
    require(n >= 1, "metrics must be non-empty")
    nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=figsize, squeeze=False)
    for i, m in enumerate(metrics):
        r, c = divmod(i, ncols)
        plot_metric_vs_param(rows, param=param, metric=m, agg=agg, ax=axes[r][c], label=None)
        axes[r][c].set_title(m)
    for j in range(n, nrows * ncols):
        r, c = divmod(j, ncols)
        axes[r][c].axis("off")
    fig.tight_layout()
    return fig, axes
def plot_summary_bars(
    summary: Mapping[str, Mapping[str, float]],
    *,
    value_key: str = "mean",
    ax=None,
):
    """Bar plot from the output of :func:`summarize_metrics`."""
    plt = _mpl()
    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure
    metrics = list(summary.keys())
    vals = [float(summary[m].get(value_key, float("nan"))) for m in metrics]
    ax.bar(metrics, vals)
    ax.set_ylabel(value_key)
    ax.set_xticks(range(len(metrics)), metrics, rotation=30, ha="right")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    return fig, ax
def save_figure(fig, path: str | Path, *, dpi: int = 150, close: bool = False) -> Path:
    """Save a matplotlib figure to *path* (default suffix: .png)."""
    p = ensure_suffix(as_path(path) or Path(path), ".png")
    ensure_parent_dir(p)
    fig.savefig(p, dpi=dpi, bbox_inches="tight")
    if close:
        _mpl().close(fig)
    return p
