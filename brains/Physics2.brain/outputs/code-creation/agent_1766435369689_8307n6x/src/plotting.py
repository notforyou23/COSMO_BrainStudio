"""Centralized plotting helpers.

Design goals:
- Consistent, publication-style matplotlib defaults.
- Deterministic, reproducible saves (stable filenames + fixed DPI/layout).
- Minimal surface area: helpers used by experiment scripts.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable, Optional, Sequence, Tuple

import matplotlib as mpl
import matplotlib.pyplot as plt
_DEFAULT_RC = {
    # Typography / sizing
    "font.size": 10.0,
    "axes.titlesize": 11.0,
    "axes.labelsize": 10.0,
    "legend.fontsize": 9.0,
    "xtick.labelsize": 9.0,
    "ytick.labelsize": 9.0,
    "figure.dpi": 120,
    "savefig.dpi": 300,
    # Clean look
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linewidth": 0.7,
    "axes.axisbelow": True,
    "lines.linewidth": 1.8,
    "lines.markersize": 4.5,
    "legend.frameon": False,
    # Determinism / stability across backends
    "figure.constrained_layout.use": True,
    "path.simplify": True,
}
def set_mpl_defaults(style: Optional[str] = "default") -> None:
    """Apply consistent defaults once per process.

    Parameters
    ----------
    style:
        Matplotlib style name. Use "default" for predictable output.
    """
    if style is not None:
        plt.style.use(style)
    mpl.rcParams.update(_DEFAULT_RC)
def slugify(name: str) -> str:
    """Convert a label into a safe, deterministic filename stem."""
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name or "figure"
@dataclass(frozen=True)
class SaveSpec:
    outdir: Path
    stem: str
    formats: Tuple[str, ...] = ("png", "pdf")
    dpi: int = 300

    def paths(self) -> Tuple[Path, ...]:
        s = slugify(self.stem)
        return tuple(self.outdir / f"{s}.{ext.lstrip('.')}" for ext in self.formats)
def figure(
    *,
    figsize: Tuple[float, float] = (5.4, 3.4),
    nrows: int = 1,
    ncols: int = 1,
    sharex: bool | str = False,
    sharey: bool | str = False,
) -> Tuple[plt.Figure, plt.Axes]:
    """Create a figure with project defaults applied."""
    set_mpl_defaults()
    fig, ax = plt.subplots(
        nrows=nrows,
        ncols=ncols,
        figsize=figsize,
        sharex=sharex,
        sharey=sharey,
    )
    return fig, ax
def save_figure(
    fig: plt.Figure,
    spec: SaveSpec,
    *,
    close: bool = True,
    bbox_inches: str = "tight",
    pad_inches: float = 0.02,
) -> Tuple[Path, ...]:
    """Save a figure deterministically to an output directory.

    Notes on determinism:
    - Fixed DPI + tight bounding box for stable rasterization.
    - Sanitized file stem via `slugify`.
    - Metadata is minimized (where supported) to avoid timestamp churn.
    """
    spec.outdir.mkdir(parents=True, exist_ok=True)

    # Supported by PDF/SVG/PS; ignored by PNG on many setups but harmless.
    metadata = {"Creator": "generated_script", "CreationDate": None, "Date": None}

    paths = spec.paths()
    for path in paths:
        ext = path.suffix.lower().lstrip(".")
        fig.savefig(
            path,
            dpi=spec.dpi,
            bbox_inches=bbox_inches,
            pad_inches=pad_inches,
            metadata=metadata if ext in {"pdf", "svg", "ps", "eps"} else None,
            transparent=False,
        )
    if close:
        plt.close(fig)
    return paths
def save_simple(
    x: Sequence[float],
    y: Sequence[float],
    *,
    outdir: Path,
    stem: str,
    xlabel: str = "x",
    ylabel: str = "y",
    title: Optional[str] = None,
    formats: Iterable[str] = ("png", "pdf"),
) -> Tuple[Path, ...]:
    """Convenience: one-line plot + save (useful for quick diagnostics)."""
    fig, ax = figure()
    ax.plot(x, y)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    return save_figure(fig, SaveSpec(Path(outdir), stem, tuple(formats)))
if __name__ == "__main__":
    # Minimal self-test / example: writes to ./output relative to CWD.
    import numpy as np

    xs = np.linspace(0, 2 * np.pi, 400)
    ys = np.sin(xs) * np.exp(-0.15 * xs)
    save_simple(
        xs,
        ys,
        outdir=Path("output"),
        stem="example_damped_sine",
        xlabel="x",
        ylabel="sin(x) e^{-0.15x}",
        title="Example plot (deterministic save)",
    )
