"""Plotting helpers for the evidence-pack pipeline.

This module renders a canonical PNG (`figure.png`) from pipeline results with
consistent styling and deterministic output across runs and environments.
""""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple, Union

import matplotlib
matplotlib.use("Agg")  # deterministic, non-interactive backend
import matplotlib.pyplot as plt
def _apply_style() -> None:
    """Apply a small, deterministic matplotlib style."""
    plt.rcParams.update(
        {
            "figure.figsize": (8.0, 4.5),
            "figure.dpi": 150,
            "savefig.dpi": 150,
            "savefig.facecolor": "white",
            "savefig.edgecolor": "white",
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "grid.linestyle": "-",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "legend.frameon": False,
            "lines.linewidth": 2.0,
            "lines.markersize": 4.0,
        }
    )
def _as_metrics(results: Mapping[str, Any]) -> Dict[str, float]:
    """Extract a stable metrics mapping from results."""
    metrics = results.get("metrics", {})
    if not isinstance(metrics, Mapping):
        return {}
    out: Dict[str, float] = {}
    for k in sorted(metrics.keys(), key=str):
        v = metrics[k]
        try:
            out[str(k)] = float(v)
        except Exception:
            continue
    return out
def _as_series(results: Mapping[str, Any]) -> Sequence[Tuple[Sequence[float], Sequence[float], str]]:
    """Extract optional time/iteration series in a normalized form.

    Supported input forms:
      - results["series"] = [{"x": [...], "y": [...], "label": "name"}, ...]
      - results["series"] = {"name": {"x": [...], "y": [...]}, ...}
    """
    series = results.get("series")
    normalized: list[Tuple[Sequence[float], Sequence[float], str]] = []
    if series is None:
        return normalized

    if isinstance(series, Mapping):
        items = [(str(k), v) for k, v in series.items()]
        for name, s in sorted(items, key=lambda t: t[0]):
            if isinstance(s, Mapping) and "x" in s and "y" in s:
                x, y = s.get("x"), s.get("y")
                if isinstance(x, Sequence) and isinstance(y, Sequence):
                    normalized.append((list(map(float, x)), list(map(float, y)), name))
        return normalized

    if isinstance(series, Sequence):
        for s in series:
            if not isinstance(s, Mapping):
                continue
            x, y = s.get("x"), s.get("y")
            label = str(s.get("label", "series"))
            if isinstance(x, Sequence) and isinstance(y, Sequence):
                normalized.append((list(map(float, x)), list(map(float, y)), label))
        normalized.sort(key=lambda t: t[2])
    return normalized
def render_canonical_figure(
    results: Mapping[str, Any],
    out_path: Union[str, Path],
    *,
    title: str = "Evidence Pack",
) -> Path:
    """Render a deterministic canonical figure from `results` to `out_path`.

    The figure includes:
      - a horizontal bar chart of numeric metrics (if present)
      - optional line plot(s) for any provided series

    Parameters
    ----------
    results:
        Pipeline results mapping (typically parsed from outputs/results.json).
    out_path:
        Destination for the PNG.
    title:
        Figure title.

    Returns
    -------
    Path to the written PNG.
    """
    _apply_style()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    metrics = _as_metrics(results)
    series = _as_series(results)

    nrows = 2 if series else 1
    fig, axes = plt.subplots(nrows=nrows, ncols=1, constrained_layout=True)
    if not isinstance(axes, Iterable):
        axes_list = [axes]
    else:
        axes_list = list(axes)

    fig.suptitle(title)

    # Metrics panel (always present but may show a note).
    ax0 = axes_list[0]
    if metrics:
        names = list(metrics.keys())
        values = [metrics[k] for k in names]
        ax0.barh(names, values, color="#4C78A8")
        ax0.set_xlabel("value")
        ax0.set_title("Metrics")
        ax0.invert_yaxis()
    else:
        ax0.text(0.5, 0.5, "No metrics", ha="center", va="center", transform=ax0.transAxes)
        ax0.set_axis_off()

    # Optional series panel.
    if series:
        ax1 = axes_list[1]
        for i, (x, y, label) in enumerate(series):
            ax1.plot(x, y, marker="o", label=label)
        ax1.set_title("Series")
        ax1.set_xlabel("x")
        ax1.set_ylabel("y")
        if len(series) > 1:
            ax1.legend(loc="best")

    # Ensure deterministic metadata as much as matplotlib allows.
    fig.savefig(
        out_path,
        format="png",
        metadata={"Software": "evidence-pack", "Title": title},
    )
    plt.close(fig)
    return out_path
