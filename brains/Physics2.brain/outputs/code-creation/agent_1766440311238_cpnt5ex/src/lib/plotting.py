"""Plotting utilities with graceful degradation.

The project treats plotting as optional: if matplotlib is unavailable, helpers
silently skip figure generation (returning False) while allowing experiments
to complete and still emit numeric/text outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
import json
import math
import os
# Optional matplotlib import -------------------------------------------------

_MPL_ERR: str | None = None
plt = None  # set when matplotlib is available


def matplotlib_available() -> bool:
    """Return True if matplotlib can be imported and configured."""
    global plt, _MPL_ERR
    if plt is not None:
        return True
    if _MPL_ERR is not None:
        return False
    try:
        import matplotlib  # type: ignore

        matplotlib.use("Agg", force=True)  # headless / CI safe
        import matplotlib.pyplot as _plt  # type: ignore

        plt = _plt
        return True
    except Exception as e:  # pragma: no cover - environment-dependent
        _MPL_ERR = f"{type(e).__name__}: {e}"
        return False
# Styling & filesystem helpers ----------------------------------------------


@dataclass(frozen=True)
class FigSpec:
    """Figure spec tuned for publication-friendly defaults."""

    width: float = 6.0
    height: float = 4.0
    dpi: int = 200
    tight: bool = True


def ensure_parent(path: os.PathLike[str] | str) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def set_pub_style() -> None:
    """Apply a clean, readable style (no-op if matplotlib missing)."""
    if not matplotlib_available():
        return
    plt.rcParams.update(
        {
            "figure.dpi": 120,
            "savefig.dpi": 300,
            "font.size": 11,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "legend.frameon": False,
        }
    )
def save_figure(fig, out_path: os.PathLike[str] | str, spec: FigSpec | None = None) -> bool:
    """Save a matplotlib figure; return False if matplotlib is unavailable."""
    if not matplotlib_available():
        return False
    spec = spec or FigSpec()
    out = ensure_parent(out_path)
    if spec.tight:
        fig.tight_layout()
    fig.savefig(out, dpi=spec.dpi, bbox_inches="tight" if spec.tight else None)
    return True


def _as_float(x: Any) -> float | None:
    try:
        if x is None:
            return None
        v = float(x)
        if math.isfinite(v):
            return v
        return None
    except Exception:
        return None
# Data loading ---------------------------------------------------------------


def load_json_records(path: os.PathLike[str] | str) -> list[dict[str, Any]]:
    """Load experiment outputs from JSON or JSONL (list of dict records)."""
    p = Path(path)
    text = p.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if text.lstrip().startswith("["):
        data = json.loads(text)
        if not isinstance(data, list):
            raise ValueError("Expected a JSON list of records")
        return [r for r in data if isinstance(r, dict)]
    records: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        if isinstance(rec, dict):
            records.append(rec)
    return records
# Plot constructors ----------------------------------------------------------


def plot_xy(
    xs: Sequence[float],
    ys: Sequence[float],
    *,
    xlabel: str = "x",
    ylabel: str = "y",
    title: str | None = None,
    label: str | None = None,
    marker: str | None = None,
):
    """Create a simple x-y line plot; returns a matplotlib Figure or None."""
    if not matplotlib_available():
        return None
    set_pub_style()
    fig, ax = plt.subplots(figsize=(6.0, 4.0))
    ax.plot(xs, ys, label=label, marker=marker)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    if label:
        ax.legend()
    return fig
def plot_metric_from_records(
    records: Iterable[Mapping[str, Any]],
    *,
    x_key: str,
    y_key: str,
    group_key: str | None = None,
    xlabel: str | None = None,
    ylabel: str | None = None,
    title: str | None = None,
):
    """Plot y_key vs x_key from record dicts; optionally grouped into series."""
    if not matplotlib_available():
        return None
    set_pub_style()
    fig, ax = plt.subplots(figsize=(6.0, 4.0))
    series: dict[str, list[tuple[float, float]]] = {}
    for r in records:
        x = _as_float(r.get(x_key))
        y = _as_float(r.get(y_key))
        if x is None or y is None:
            continue
        g = str(r.get(group_key)) if group_key else "series"
        series.setdefault(g, []).append((x, y))
    for name, pts in sorted(series.items(), key=lambda kv: kv[0]):
        pts.sort(key=lambda t: t[0])
        ax.plot([p[0] for p in pts], [p[1] for p in pts], label=name if group_key else None)
    ax.set_xlabel(xlabel or x_key)
    ax.set_ylabel(ylabel or y_key)
    if title:
        ax.set_title(title)
    if group_key:
        ax.legend()
    return fig
