"""Deterministic plotting utilities.

This module produces a stable Matplotlib PNG artifact with controlled rendering
settings for reproducible pipeline runs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence, Tuple, Union

import numpy as np

import matplotlib
matplotlib.use("Agg")  # must be set before importing pyplot
import matplotlib.pyplot as plt
@dataclass(frozen=True)
class PlotSpec:
    title: str = "Deterministic Figure"
    xlabel: str = "x"
    ylabel: str = "y"
    width_in: float = 6.4
    height_in: float = 4.0
    dpi: int = 120
    line_color: str = "#1f77b4"
    grid_color: str = "#d9d9d9"


def _apply_deterministic_rcparams(dpi: int) -> None:
    matplotlib.rcParams.update(
        {
            "figure.dpi": dpi,
            "savefig.dpi": dpi,
            "figure.figsize": (6.4, 4.0),
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "black",
            "axes.linewidth": 1.0,
            "axes.grid": True,
            "grid.color": "#d9d9d9",
            "grid.linewidth": 0.8,
            "grid.linestyle": "-",
            "font.family": "DejaVu Sans",
            "font.size": 10.0,
            "axes.titlesize": 12.0,
            "axes.labelsize": 10.0,
            "xtick.labelsize": 9.0,
            "ytick.labelsize": 9.0,
            "legend.fontsize": 9.0,
            "lines.linewidth": 2.0,
            "lines.antialiased": True,
            "patch.antialiased": True,
            "path.simplify": False,
            "text.usetex": False,
            "axes.unicode_minus": False,
            "date.converter": "concise",
        }
    )
def _to_1d_float_array(values: Union[Sequence[float], np.ndarray]) -> np.ndarray:
    arr = np.asarray(values, dtype=float).reshape(-1)
    if arr.size == 0:
        raise ValueError("x/y must be non-empty")
    return arr


def make_default_series(n: int = 200) -> Tuple[np.ndarray, np.ndarray]:
    x = np.linspace(0.0, 2.0 * np.pi, int(n), dtype=float)
    y = np.sin(x) + 0.25 * np.cos(2.0 * x)
    return x, y
def save_deterministic_figure(
    x: Union[Sequence[float], np.ndarray],
    y: Union[Sequence[float], np.ndarray],
    out_path: Union[str, Path],
    spec: Optional[PlotSpec] = None,
) -> Path:
    """Create and save a deterministic PNG figure.

    Parameters
    ----------
    x, y:
        1D numeric sequences of equal length.
    out_path:
        Destination path (typically outputs/figure.png).
    spec:
        PlotSpec for titles/labels and rendering settings.

    Returns
    -------
    Path to the written file.
    """
    spec = spec or PlotSpec()
    x_arr = _to_1d_float_array(x)
    y_arr = _to_1d_float_array(y)
    if x_arr.shape != y_arr.shape:
        raise ValueError("x and y must have the same length")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    _apply_deterministic_rcparams(spec.dpi)
    figsize = (float(spec.width_in), float(spec.height_in))

    fig, ax = plt.subplots(figsize=figsize, dpi=spec.dpi, constrained_layout=False)
    try:
        ax.plot(x_arr, y_arr, color=spec.line_color)
        ax.set_title(spec.title)
        ax.set_xlabel(spec.xlabel)
        ax.set_ylabel(spec.ylabel)
        ax.grid(True, color=spec.grid_color)
        ax.margins(x=0.02, y=0.08)

        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)

        fig.tight_layout(pad=0.6)

        # Avoid non-deterministic metadata in output files.
        fig.savefig(
            out_path,
            format="png",
            dpi=spec.dpi,
            facecolor="white",
            edgecolor="white",
            bbox_inches="tight",
            pad_inches=0.08,
            metadata={"Software": "generated_script_pipeline", "CreationTime": None},
        )
    finally:
        plt.close(fig)

    return out_path
