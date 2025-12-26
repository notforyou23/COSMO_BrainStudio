"""Centralized plotting and table-writing helpers.

Design goals:
- Deterministic styling (consistent rcParams).
- One call to save a figure to PNG/PDF with tight layout.
- One call to write tabular summaries to CSV (pandas optional).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import csv

import matplotlib as mpl
import matplotlib.pyplot as plt
@dataclass(frozen=True)
class PlotStyle:
    """Small bundle of style choices for reproducible figures."""

    dpi: int = 200
    figsize: tuple[float, float] = (6.0, 4.0)
    font_size: int = 11
    line_width: float = 1.6
    grid: bool = True
    color_cycle: Sequence[str] = (
        "#4C78A8", "#F58518", "#54A24B", "#E45756",
        "#72B7B2", "#B279A2", "#FF9DA6", "#9D755D",
    )


_DEFAULT_STYLE = PlotStyle()


def set_mpl_style(style: PlotStyle | None = None) -> PlotStyle:
    """Apply a deterministic matplotlib style and return the applied style."""
    s = style or _DEFAULT_STYLE
    mpl.rcParams.update(
        {
            "figure.dpi": s.dpi,
            "savefig.dpi": s.dpi,
            "figure.figsize": s.figsize,
            "font.size": s.font_size,
            "axes.titlesize": s.font_size + 1,
            "axes.labelsize": s.font_size,
            "legend.fontsize": s.font_size - 1,
            "xtick.labelsize": s.font_size - 1,
            "ytick.labelsize": s.font_size - 1,
            "axes.grid": s.grid,
            "grid.alpha": 0.25,
            "axes.linewidth": 0.8,
            "lines.linewidth": s.line_width,
            "axes.prop_cycle": mpl.cycler(color=list(s.color_cycle)),
            "savefig.bbox": "tight",
        }
    )
    return s
def _as_path(p: str | Path) -> Path:
    return p if isinstance(p, Path) else Path(p)


def ensure_dir(path: str | Path) -> Path:
    """Create directory if needed and return it as a Path."""
    p = _as_path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_figure(
    fig: mpl.figure.Figure,
    out_base: str | Path,
    formats: Sequence[str] = ("png", "pdf"),
    dpi: int | None = None,
    close: bool = True,
) -> list[Path]:
    """Save figure to multiple formats.

    Parameters
    ----------
    fig:
        Matplotlib figure.
    out_base:
        Output path without extension (e.g., outputs/figures/corr_vs_T).
    formats:
        Iterable of extensions to write.
    dpi:
        Override DPI for this save call.
    close:
        Whether to close the figure after saving (recommended for batch runs).
    """
    out_base = _as_path(out_base)
    ensure_dir(out_base.parent)
    fig.tight_layout()
    written: list[Path] = []
    for ext in formats:
        ext = ext.lstrip(".").lower()
        out = out_base.with_suffix("." + ext)
        fig.savefig(out, dpi=dpi, bbox_inches="tight")
        written.append(out)
    if close:
        plt.close(fig)
    return written
def new_figure(
    *,
    style: PlotStyle | None = None,
    figsize: tuple[float, float] | None = None,
) -> tuple[mpl.figure.Figure, mpl.axes.Axes]:
    """Create a new figure+axes with the project default style."""
    s = set_mpl_style(style)
    fig, ax = plt.subplots(figsize=figsize or s.figsize)
    return fig, ax
def write_csv(
    rows: Iterable[Mapping[str, Any]] | Any,
    out_path: str | Path,
    *,
    index: bool = False,
) -> Path:
    """Write a CSV summary table.

    Accepts either:
    - pandas.DataFrame (if pandas is installed), or
    - an iterable of dict-like rows.

    Parameters
    ----------
    index:
        Only relevant for pandas DataFrames; ignored otherwise.
    """
    out_path = _as_path(out_path)
    ensure_dir(out_path.parent)

    # pandas path (optional dependency at runtime)
    try:
        import pandas as pd  # type: ignore
    except Exception:
        pd = None  # type: ignore

    if pd is not None and hasattr(rows, "to_csv"):
        rows.to_csv(out_path, index=index)  # type: ignore[attr-defined]
        return out_path

    rows_list = list(rows)  # type: ignore[arg-type]
    if not rows_list:
        out_path.write_text("", encoding="utf-8")
        return out_path

    fieldnames = sorted({k for r in rows_list for k in r.keys()})
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows_list:
            w.writerow({k: r.get(k, "") for k in fieldnames})
    return out_path
