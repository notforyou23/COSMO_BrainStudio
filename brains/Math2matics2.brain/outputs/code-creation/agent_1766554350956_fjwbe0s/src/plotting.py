from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

import matplotlib
matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt


def _stable_series(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    series = results.get("series", None)
    if not isinstance(series, list):
        return []
    out: List[Dict[str, Any]] = []
    for s in series:
        if not isinstance(s, dict):
            continue
        x = s.get("x", [])
        y = s.get("y", [])
        if not isinstance(x, list) or not isinstance(y, list) or len(x) != len(y):
            continue
        label = s.get("label", "series")
        out.append({"x": list(x), "y": list(y), "label": str(label)})
    out.sort(key=lambda d: d["label"])
    return out


def _apply_deterministic_style() -> None:
    plt.rcParams.update(
        {
            "figure.figsize": (8.0, 5.0),
            "figure.dpi": 100,
            "savefig.dpi": 100,
            "savefig.facecolor": "white",
            "savefig.edgecolor": "white",
            "savefig.bbox": "tight",
            "savefig.pad_inches": 0.10,
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.titlesize": 12,
            "axes.labelsize": 11,
            "legend.fontsize": 10,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "lines.linewidth": 2.0,
            "lines.markersize": 4.0,
            "path.simplify": False,
            "axes.prop_cycle": plt.cycler(
                color=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]
            ),
        }
    )


def create_figure(
    results: Dict[str, Any],
    out_path: Union[str, Path],
    title: str = "Deterministic Pipeline Figure",
) -> Path:
    """
    Create a deterministic PNG based on `results`.

    Expected (optional) keys in results:
      - series: list of {x: [..], y: [..], label: str}
      - summary: dict (shown as a compact text box)
    """
    _apply_deterministic_style()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots()

    series = _stable_series(results)
    if series:
        for s in series:
            ax.plot(s["x"], s["y"], marker="o", label=s["label"])
        ax.legend(loc="best", frameon=True, framealpha=0.9)
        ax.set_xlabel(results.get("xlabel", "x"))
        ax.set_ylabel(results.get("ylabel", "y"))
    else:
        ax.set_axis_off()
        summary = results.get("summary", results)
        try:
            text = json.dumps(summary, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            text = str(summary)
        ax.text(
            0.01,
            0.99,
            text,
            ha="left",
            va="top",
            transform=ax.transAxes,
            fontsize=9,
            family="DejaVu Sans Mono",
            wrap=True,
        )

    ax.set_title(title)

    # Avoid embedding timestamps/hostnames in PNG metadata for determinism.
    fig.savefig(out_path, format="png", metadata={})
    plt.close(fig)
    return out_path
