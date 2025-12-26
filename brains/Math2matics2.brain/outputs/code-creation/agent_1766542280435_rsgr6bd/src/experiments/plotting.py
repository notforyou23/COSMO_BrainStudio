"""Matplotlib plotting utilities for experiment sweep results.

Provides:
- Consistent styling via :class:`PlotStyle`
- Common plots for sweep results (line plots and 2D heatmaps)
- Export helpers to save figures as PNG/SVG

Functions accept either a pandas.DataFrame (preferred) or a mapping of arrays.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Sequence, Tuple, Union

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt

try:  # optional dependency
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover
    pd = None  # type: ignore

@dataclass(frozen=True)
class PlotStyle:
    fontsize: int = 11
    dpi: int = 180
    grid: bool = True
    figsize: Tuple[float, float] = (6.0, 3.6)

    def apply(self) -> None:
        mpl.rcParams.update(
            {
                "figure.dpi": self.dpi,
                "savefig.dpi": self.dpi,
                "font.size": self.fontsize,
                "axes.grid": self.grid,
                "axes.spines.top": False,
                "axes.spines.right": False,
                "axes.titlesize": self.fontsize + 1,
                "axes.labelsize": self.fontsize,
                "legend.fontsize": self.fontsize - 1,
                "xtick.labelsize": self.fontsize - 1,
                "ytick.labelsize": self.fontsize - 1,
                "lines.linewidth": 2.0,
                "grid.alpha": 0.25,
            }
        )


DEFAULT_STYLE = PlotStyle()

def ensure_dir(path: Union[str, Path]) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_figure(
    fig: mpl.figure.Figure,
    outdir: Union[str, Path],
    stem: str,
    formats: Sequence[str] = ("png", "svg"),
    dpi: Optional[int] = None,
    transparent: bool = False,
) -> Mapping[str, Path]:
    """Save figure to multiple formats and return written paths."""
    outdir = ensure_dir(outdir)
    paths: dict[str, Path] = {}
    for ext in formats:
        ext = ext.lstrip(".")
        p = outdir / f"{stem}.{ext}"
        fig.savefig(p, bbox_inches="tight", dpi=dpi or DEFAULT_STYLE.dpi, transparent=transparent)
        paths[ext] = p
    return paths

def _as_array(x):
    if pd is not None and isinstance(x, pd.Series):
        return x.to_numpy()
    return np.asarray(x)


def _get_column(data, key: str):
    if pd is not None and isinstance(data, pd.DataFrame):
        return data[key]
    if isinstance(data, Mapping):
        return data[key]
    raise TypeError("data must be a pandas.DataFrame or a mapping of arrays")

def plot_sweep_lines(
    data,
    x: str,
    y: str,
    group: Optional[str] = None,
    *,
    title: Optional[str] = None,
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    ax: Optional[mpl.axes.Axes] = None,
    style: PlotStyle = DEFAULT_STYLE,
    legend: bool = True,
) -> mpl.axes.Axes:
    """Line plot for a 1D sweep; optionally grouped by another parameter."""
    style.apply()
    if ax is None:
        _, ax = plt.subplots(figsize=style.figsize)

    if group is None:
        ax.plot(_as_array(_get_column(data, x)), _as_array(_get_column(data, y)), label=y)
    else:
        if pd is not None and isinstance(data, pd.DataFrame):
            for gv, df_g in data.groupby(group):
                ax.plot(_as_array(df_g[x]), _as_array(df_g[y]), label=f"{group}={gv}")
        else:
            g = _as_array(_get_column(data, group))
            xv = _as_array(_get_column(data, x))
            yv = _as_array(_get_column(data, y))
            for gv in np.unique(g):
                m = g == gv
                ax.plot(xv[m], yv[m], label=f"{group}={gv}")

    ax.set_title(title or f"{y} vs {x}")
    ax.set_xlabel(xlabel or x)
    ax.set_ylabel(ylabel or y)
    if legend:
        ax.legend(frameon=False)
    return ax

def plot_heatmap(
    data,
    x: str,
    y: str,
    z: str,
    *,
    title: Optional[str] = None,
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    cmap: str = "viridis",
    ax: Optional[mpl.axes.Axes] = None,
    style: PlotStyle = DEFAULT_STYLE,
    colorbar: bool = True,
) -> mpl.axes.Axes:
    """Heatmap for a 2D sweep stored in long format (x, y, z columns)."""
    style.apply()
    if ax is None:
        _, ax = plt.subplots(figsize=style.figsize)

    xs = np.unique(_as_array(_get_column(data, x)))
    ys = np.unique(_as_array(_get_column(data, y)))
    Z = np.full((len(ys), len(xs)), np.nan, dtype=float)

    xv = _as_array(_get_column(data, x))
    yv = _as_array(_get_column(data, y))
    zv = _as_array(_get_column(data, z)).astype(float)

    x_index = {v: i for i, v in enumerate(xs)}
    y_index = {v: i for i, v in enumerate(ys)}
    for xi, yi, zi in zip(xv, yv, zv):
        Z[y_index[yi], x_index[xi]] = zi

    im = ax.imshow(
        Z,
        origin="lower",
        aspect="auto",
        cmap=cmap,
        extent=(float(xs.min()), float(xs.max()), float(ys.min()), float(ys.max())),
    )
    ax.set_title(title or f"{z} heatmap")
    ax.set_xlabel(xlabel or x)
    ax.set_ylabel(ylabel or y)
    if colorbar:
        plt.colorbar(im, ax=ax, label=z, fraction=0.046, pad=0.04)
    return ax

def finalize_and_save(
    ax: mpl.axes.Axes,
    outdir: Union[str, Path],
    stem: str,
    *,
    formats: Sequence[str] = ("png", "svg"),
    close: bool = True,
) -> Mapping[str, Path]:
    """Convenience wrapper: layout, save figure, optionally close."""
    fig = ax.figure
    fig.tight_layout()
    paths = save_figure(fig, outdir, stem, formats=formats)
    if close:
        plt.close(fig)
    return paths
