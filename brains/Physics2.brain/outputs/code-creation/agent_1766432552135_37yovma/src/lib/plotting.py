"""
Plotting helpers for consistent styling and deterministic figure saving.

Design goals
------------
- Provide a small, dependency-light wrapper around matplotlib.
- Centralize rcParams so all toy experiments share consistent aesthetics.
- Make saving figures reproducible (tight layout, fixed dpi, deterministic metadata).

Example
-------
from pathlib import Path
import numpy as np
from src.lib.plotting import apply_style, new_fig, save_fig

apply_style()
fig, ax = new_fig()
x = np.linspace(0, 1, 200)
ax.plot(x, np.sin(2*np.pi*x), label="signal")
ax.set(xlabel="x", ylabel="y", title="Demo")
ax.legend()
save_fig(fig, Path("out/demo"), formats=("png","pdf"))
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence, Tuple

import matplotlib as mpl
import matplotlib.pyplot as plt


_DEFAULT_STYLE = {
    # Typography
    "font.size": 11,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "legend.fontsize": 10,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    # Lines
    "lines.linewidth": 1.6,
    "lines.markersize": 5,
    # Layout / look
    "figure.dpi": 120,
    "savefig.dpi": 200,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linestyle": "-",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "legend.frameon": False,
    "axes.prop_cycle": mpl.cycler(color=[
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    ]),
    # Deterministic output: embed minimal metadata where possible
    "svg.hashsalt": "reproducible-toy-experiments",
}
@dataclass(frozen=True)
class FigSpec:
    """Convenience bundle for consistent figure creation."""
    figsize: Tuple[float, float] = (5.2, 3.4)
    constrained_layout: bool = True
    sharex: bool = False
    sharey: bool = False


_STYLE_APPLIED = False


def apply_style(extra: Optional[dict] = None) -> None:
    """
    Apply project-wide matplotlib rcParams.

    Parameters
    ----------
    extra:
        Optional dict of rcParams to override the defaults.
    """
    global _STYLE_APPLIED
    params = dict(_DEFAULT_STYLE)
    if extra:
        params.update(extra)
    mpl.rcParams.update(params)
    _STYLE_APPLIED = True


def new_fig(
    spec: FigSpec = FigSpec(),
    nrows: int = 1,
    ncols: int = 1,
) -> Tuple[plt.Figure, plt.Axes]:
    """Create a styled figure/axes pair (or axes array if nrows*ncols>1)."""
    if not _STYLE_APPLIED:
        apply_style()
    fig, axes = plt.subplots(
        nrows=nrows,
        ncols=ncols,
        figsize=spec.figsize,
        constrained_layout=spec.constrained_layout,
        sharex=spec.sharex,
        sharey=spec.sharey,
    )
    return fig, axes
def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def save_fig(
    fig: plt.Figure,
    basepath: Path,
    *,
    formats: Sequence[str] = ("png",),
    dpi: Optional[int] = None,
    transparent: bool = False,
    close: bool = True,
) -> Iterable[Path]:
    """
    Save a figure to one or more formats.

    Parameters
    ----------
    fig:
        Matplotlib figure.
    basepath:
        Output path without suffix (e.g., Path("out/figure_01")).
    formats:
        File extensions to write (e.g., ("png","pdf","svg")).
    dpi:
        Override dpi; if None, uses rcParams["savefig.dpi"].
    transparent:
        Forwarded to savefig; defaults False for paper-like backgrounds.
    close:
        If True, closes the figure after saving to reduce memory usage.

    Returns
    -------
    Iterable[Path]:
        Paths written.
    """
    if not _STYLE_APPLIED:
        apply_style()

    written = []
    for fmt in formats:
        fmt = fmt.lstrip(".").lower()
        out = basepath.with_suffix(f".{fmt}")
        _ensure_parent(out)
        metadata = None
        # Keep metadata minimal/deterministic where supported.
        if fmt in {"png", "pdf", "svg"}:
            metadata = {"Creator": "generated_script_1766432556417", "Title": out.stem}
        fig.savefig(
            out,
            dpi=dpi,
            bbox_inches="tight",
            pad_inches=0.02,
            transparent=transparent,
            metadata=metadata,
        )
        written.append(out)

    if close:
        plt.close(fig)
    return written


def add_panel_label(ax: plt.Axes, label: str, *, x: float = 0.0, y: float = 1.02) -> None:
    """Add a panel label like '(a)' in axes coordinates."""
    ax.text(
        x, y, label,
        transform=ax.transAxes,
        ha="left", va="bottom",
        fontweight="bold",
    )
