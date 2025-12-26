\"\"\"Deterministic plotting utilities.

This module renders a stable Matplotlib figure derived solely from provided
run results and saves it to a fixed filename (e.g., /outputs/figure.png).
\"\"\"

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence, Tuple, List, Any

import matplotlib

# Ensure headless, deterministic backend selection.
matplotlib.use("Agg", force=True)  # must be set before pyplot import
import matplotlib.pyplot as plt  # noqa: E402
def _as_float_list(obj: Any) -> List[float]:
    \"\"\"Best-effort conversion to a list of floats (deterministic ordering).\"\"\"
    if obj is None:
        return []
    if isinstance(obj, (list, tuple)):
        out: List[float] = []
        for x in obj:
            try:
                out.append(float(x))
            except Exception:
                continue
        return out
    # Allow numpy arrays without importing numpy explicitly.
    if hasattr(obj, "tolist"):
        try:
            return _as_float_list(obj.tolist())
        except Exception:
            return []
    return []


def _extract_series(results: Mapping[str, Any]) -> Tuple[List[float], List[float]]:
    \"\"\"Extract a (x, y) series from results.

    Supported inputs:
    - results['series'] = {'x': [...], 'y': [...]}
    - results['series'] = [[x0, y0], [x1, y1], ...]
    - results['values'] = [...] (x = 0..n-1)
    \"\"\"
    series = results.get("series")
    if isinstance(series, Mapping):
        x = _as_float_list(series.get("x"))
        y = _as_float_list(series.get("y"))
        n = min(len(x), len(y))
        return x[:n], y[:n]
    if isinstance(series, (list, tuple)) and series and isinstance(series[0], (list, tuple)):
        x: List[float] = []
        y: List[float] = []
        for pair in series:
            if not isinstance(pair, (list, tuple)) or len(pair) < 2:
                continue
            try:
                x.append(float(pair[0]))
                y.append(float(pair[1]))
            except Exception:
                continue
        n = min(len(x), len(y))
        return x[:n], y[:n]

    values = _as_float_list(results.get("values"))
    if values:
        return list(range(len(values))), values

    # Fallback: stable synthetic series from numeric scalar keys.
    numeric_items = []
    for k in sorted(results.keys(), key=str):
        v = results.get(k)
        try:
            numeric_items.append((str(k), float(v)))
        except Exception:
            continue
    if numeric_items:
        y = [v for _, v in numeric_items]
        return list(range(len(y))), y
    return [0.0, 1.0, 2.0, 3.0], [0.0, 0.25, 0.5, 0.75]
def _extract_metrics(results: Mapping[str, Any], max_items: int = 8) -> Tuple[List[str], List[float]]:
    \"\"\"Extract a small set of scalar metrics for a bar chart.\"\"\"
    metrics = results.get("metrics")
    items: List[Tuple[str, float]] = []
    if isinstance(metrics, Mapping):
        for k in sorted(metrics.keys(), key=str):
            try:
                items.append((str(k), float(metrics[k])))
            except Exception:
                continue
    else:
        for k in sorted(results.keys(), key=str):
            if k in {"series", "values", "metadata"}:
                continue
            try:
                items.append((str(k), float(results[k])))
            except Exception:
                continue
    items = items[:max_items]
    labels = [k for k, _ in items]
    values = [v for _, v in items]
    return labels, values


def save_figure(results: Mapping[str, Any], output_path: str | Path = "/outputs/figure.png") -> Path:
    \"\"\"Create and save a deterministic figure for the provided results.\"\"\"
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Fixed, explicit styling for determinism.
    plt.rcParams.update(
        {
            "figure.figsize": (8.0, 4.5),
            "figure.dpi": 100,
            "savefig.dpi": 100,
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "lines.linewidth": 2.0,
            "lines.markersize": 4.0,
            "legend.frameon": False,
        }
    )

    x, y = _extract_series(results)
    m_labels, m_values = _extract_metrics(results)

    fig = plt.figure(constrained_layout=False)
    gs = fig.add_gridspec(1, 2, width_ratios=[2.2, 1.0])

    ax0 = fig.add_subplot(gs[0, 0])
    ax0.plot(x, y, color="#1f77b4", marker="o")
    ax0.set_title("Deterministic run series")
    ax0.set_xlabel("x")
    ax0.set_ylabel("y")
    if len(x) > 1:
        ax0.set_xlim(min(x), max(x))

    ax1 = fig.add_subplot(gs[0, 1])
    if m_labels:
        ax1.barh(m_labels, m_values, color="#ff7f0e")
        ax1.set_title("Metrics")
        ax1.grid(True, axis="x")
    else:
        ax1.text(0.5, 0.5, "No metrics", ha="center", va="center")
        ax1.set_axis_off()

    fig.suptitle("Deterministic Runner Output", y=0.98)

    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out, format="png", bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)
    return out


__all__ = ["save_figure"]
