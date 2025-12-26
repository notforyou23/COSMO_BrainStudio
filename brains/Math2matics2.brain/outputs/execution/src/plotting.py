"""
Deterministic plotting helpers.

Goal: render figure.png with fixed style, layout, and metadata to make output
byte-stable where feasible across runs on the same environment.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence, Tuple

import matplotlib
matplotlib.use("Agg", force=True)  # must be set before importing pyplot

import matplotlib.pyplot as plt


_FIXED_RC = {
    # Style/layout determinism
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
    "axes.grid": True,
    "grid.alpha": 0.35,
    "grid.linestyle": "-",
    "grid.linewidth": 0.6,
    "axes.edgecolor": "black",
    "axes.linewidth": 0.8,
    "axes.titlesize": 12,
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "legend.frameon": True,
    "legend.framealpha": 0.9,
    "legend.fancybox": False,
    "lines.linewidth": 1.8,
    "lines.markersize": 4.5,
    "font.family": "DejaVu Sans",
    "mathtext.default": "regular",
    "figure.dpi": 100,
    "savefig.dpi": 100,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.05,
    "path.simplify": False,  # avoid backend-dependent simplification
    "axes.prop_cycle": plt.cycler(
        color=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
    ),
}


def apply_deterministic_style() -> None:
    """Apply deterministic matplotlib settings (idempotent)."""
    matplotlib.rcParams.update(_FIXED_RC)
    # Avoid runtime-dependent font cache warnings in tests by keeping defaults; the
    # actual font selection is pinned via rcParams above.
def _canonical_xy(data: Mapping[str, Any]) -> Tuple[Sequence[float], Sequence[float]]:
    if "x" in data and "y" in data:
        return data["x"], data["y"]
    if "series" in data and isinstance(data["series"], Mapping):
        series = data["series"]
        if "x" in series and "y" in series:
            return series["x"], series["y"]
    raise KeyError("Expected keys ('x','y') or ('series'->'x','y') in results data.")


def _stable_title(data: Mapping[str, Any]) -> str:
    for k in ("title", "name", "run_id"):
        if k in data and isinstance(data[k], str) and data[k].strip():
            return data[k].strip()
    return "Deterministic Figure"


def make_figure(figsize: Tuple[float, float] = (6.4, 4.0)):
    """Create a deterministic figure/axes pair."""
    apply_deterministic_style()
    fig, ax = plt.subplots(figsize=figsize, constrained_layout=False)
    return fig, ax


def plot_results(ax, results: Mapping[str, Any]) -> None:
    """Plot a simple line chart from results dict using stable ordering."""
    x, y = _canonical_xy(results)
    label = None
    if "label" in results and isinstance(results["label"], str):
        label = results["label"]
    ax.plot(list(x), list(y), marker="o", label=label)

    ax.set_title(_stable_title(results))
    ax.set_xlabel(results.get("xlabel", "x"))
    ax.set_ylabel(results.get("ylabel", "y"))

    # Stable ticks/limits if provided
    if "xlim" in results and isinstance(results["xlim"], (list, tuple)) and len(results["xlim"]) == 2:
        ax.set_xlim(results["xlim"][0], results["xlim"][1])
    if "ylim" in results and isinstance(results["ylim"], (list, tuple)) and len(results["ylim"]) == 2:
        ax.set_ylim(results["ylim"][0], results["ylim"][1])

    if label:
        ax.legend(loc="best")

    # Deterministic layout
    fig = ax.figure
    fig.tight_layout(pad=0.2)
def save_figure_png(results: Mapping[str, Any], out_path: Path) -> None:
    """Render and save figure as PNG with stable metadata.

    Note: full byte-for-byte stability depends on matplotlib/Pillow versions;
    setting fixed metadata and avoiding timestamps improves reproducibility.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = make_figure()
    try:
        plot_results(ax, results)
        # Use fixed metadata to avoid embedding timestamps or environment-specific fields.
        metadata = {
            "Software": "generated_script_1766554221975",
            "Title": _stable_title(results),
            "Author": "",
            "Description": "Deterministic pipeline output",
            "Creation Time": "1970-01-01T00:00:00Z",
        }
        fig.savefig(
            out_path,
            format="png",
            dpi=_FIXED_RC["savefig.dpi"],
            facecolor=_FIXED_RC["savefig.facecolor"],
            bbox_inches=_FIXED_RC["savefig.bbox"],
            pad_inches=_FIXED_RC["savefig.pad_inches"],
            metadata=metadata,
        )
    finally:
        plt.close(fig)
