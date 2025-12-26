"""Deterministic plotting helpers.

Goals:
- Stable styling (rcParams) and layout defaults.
- Byte-stable PNG output where feasible by re-encoding via Pillow with fixed params.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple, Union

import matplotlib

# Must be set before importing pyplot.
matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt  # noqa: E402
try:
    from PIL import Image  # type: ignore
except Exception as e:  # pragma: no cover
    Image = None  # type: ignore


@dataclass(frozen=True)
class PlotStyle:
    dpi: int = 100
    figsize: Tuple[float, float] = (6.4, 4.0)
    facecolor: str = "white"
    edgecolor: str = "white"
    line_width: float = 2.0
    grid: bool = True
    tight_layout: bool = True
    transparent: bool = False
    compress_level: int = 9


_DETERMINISTIC_RCPARAMS: Dict[str, Any] = {
    "figure.dpi": 100,
    "savefig.dpi": 100,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "savefig.edgecolor": "white",
    "savefig.transparent": False,
    "font.family": "DejaVu Sans",
    "font.size": 10.0,
    "axes.titlesize": 12.0,
    "axes.labelsize": 10.0,
    "xtick.labelsize": 9.0,
    "ytick.labelsize": 9.0,
    "legend.fontsize": 9.0,
    "axes.grid": True,
    "grid.color": "#d0d0d0",
    "grid.linewidth": 0.8,
    "grid.alpha": 1.0,
    "axes.linewidth": 0.8,
    "lines.linewidth": 2.0,
    "lines.antialiased": True,
    "path.simplify": False,
    "path.snap": False,
    "text.usetex": False,
    "mathtext.default": "regular",
    "axes.unicode_minus": True,
    "image.interpolation": "nearest",
    "image.resample": False,
    "figure.autolayout": False,
}
def setup_deterministic_style(extra_rcparams: Optional[Dict[str, Any]] = None) -> None:
    """Apply a deterministic matplotlib style globally."""
    matplotlib.rcdefaults()
    matplotlib.rcParams.update(_DETERMINISTIC_RCPARAMS)
    if extra_rcparams:
        matplotlib.rcParams.update(dict(extra_rcparams))


def _coerce_path(p: Union[str, Path]) -> Path:
    return p if isinstance(p, Path) else Path(p)


def save_figure_png(
    fig: "plt.Figure",
    out_path: Union[str, Path],
    *,
    style: PlotStyle = PlotStyle(),
    metadata: Optional[Dict[str, str]] = None,
) -> Path:
    """Save a figure to a PNG as deterministically as feasible.

    Strategy:
    1) Save to an in-memory PNG via matplotlib with fixed params.
    2) Re-encode via Pillow (if available) to reduce non-deterministic chunks/metadata.
    """
    out_path = _coerce_path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    md: Dict[str, str] = {"Software": "matplotlib"}
    if metadata:
        md.update({str(k): str(v) for k, v in metadata.items()})

    buf = BytesIO()
    fig.savefig(
        buf,
        format="png",
        dpi=style.dpi,
        facecolor=style.facecolor,
        edgecolor=style.edgecolor,
        transparent=style.transparent,
        bbox_inches="tight",
        pad_inches=0.1,
        metadata=md,
    )
    plt.close(fig)
    raw = buf.getvalue()

    if Image is None:
        out_path.write_bytes(raw)
        return out_path

    with Image.open(BytesIO(raw)) as im:
        # Normalize mode for stable encoding.
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGBA")
        else:
            im = im.copy()

        save_kwargs: Dict[str, Any] = {
            "format": "PNG",
            "optimize": False,
            "compress_level": int(style.compress_level),
        }
        # Avoid writing textual metadata chunks for stability.
        im.save(out_path, **save_kwargs)

    return out_path
def line_plot(
    x: Sequence[float],
    y: Sequence[float],
    *,
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    style: PlotStyle = PlotStyle(),
    color: str = "#1f77b4",
) -> "plt.Figure":
    """Create a deterministic line plot figure (no saving)."""
    setup_deterministic_style()
    fig, ax = plt.subplots(figsize=style.figsize, dpi=style.dpi)
    ax.plot(list(x), list(y), color=color, linewidth=style.line_width)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(style.grid)
    if style.tight_layout:
        fig.tight_layout()
    return fig


def bar_plot(
    categories: Sequence[str],
    values: Sequence[float],
    *,
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    style: PlotStyle = PlotStyle(),
    color: str = "#ff7f0e",
) -> "plt.Figure":
    """Create a deterministic bar plot figure (no saving)."""
    setup_deterministic_style()
    fig, ax = plt.subplots(figsize=style.figsize, dpi=style.dpi)
    ax.bar(list(categories), list(values), color=color, edgecolor="black", linewidth=0.6)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(style.grid, axis="y")
    if style.tight_layout:
        fig.tight_layout()
    return fig
