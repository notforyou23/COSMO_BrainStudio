from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

import matplotlib
matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import numpy as np
@dataclass(frozen=True)
class PlotSpec:
    width_in: float = 6.4
    height_in: float = 4.0
    dpi: int = 100
    seed: int = 0
    style: str = "default"
    line_color: str = "#1f77b4"
    grid: bool = True
def _as_xy(results: Dict[str, Any]) -> Tuple[np.ndarray, np.ndarray]:
    if isinstance(results.get("x"), (list, tuple)) and isinstance(results.get("y"), (list, tuple)):
        x = np.asarray(results["x"], dtype=float)
        y = np.asarray(results["y"], dtype=float)
        return x, y

    if isinstance(results.get("values"), (list, tuple)):
        y = np.asarray(results["values"], dtype=float)
        x = np.arange(len(y), dtype=float)
        return x, y

    if isinstance(results.get("metrics"), dict):
        items = sorted((str(k), results["metrics"][k]) for k in results["metrics"].keys())
        labels = [k for k, _ in items]
        y = np.asarray([float(v) for _, v in items], dtype=float)
        x = np.arange(len(y), dtype=float)
        return x, y

    raise ValueError("Unsupported results structure for plotting; expected keys: (x,y) or values or metrics.")
def _configure_matplotlib(spec: PlotSpec) -> None:
    np.random.seed(spec.seed)
    try:
        plt.style.use(spec.style)
    except Exception:
        plt.style.use("default")

    matplotlib.rcParams.update(
        {
            "figure.figsize": (spec.width_in, spec.height_in),
            "figure.dpi": spec.dpi,
            "savefig.dpi": spec.dpi,
            "font.family": "DejaVu Sans",
            "axes.grid": spec.grid,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "lines.linewidth": 2.0,
            "path.simplify": False,
            "axes.unicode_minus": False,
        }
    )
def save_figure_png(
    results: Dict[str, Any],
    out_path: Union[str, Path],
    *,
    spec: Optional[PlotSpec] = None,
) -> Path:
    """
    Deterministically generate a PNG plot from computed results.

    Determinism controls:
    - fixed figure size + dpi
    - fixed style + rcParams
    - fixed RNG seed
    - post-process PNG with PIL to strip metadata and use fixed compression settings
    """
    spec = spec or PlotSpec()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    _configure_matplotlib(spec)
    x, y = _as_xy(results)

    fig, ax = plt.subplots()
    title = results.get("title") or results.get("name") or "Results"
    ax.set_title(str(title))
    ax.set_xlabel(str(results.get("xlabel") or "x"))
    ax.set_ylabel(str(results.get("ylabel") or "y"))

    if isinstance(results.get("metrics"), dict) and not (isinstance(results.get("x"), (list, tuple)) and isinstance(results.get("y"), (list, tuple))):
        items = sorted((str(k), results["metrics"][k]) for k in results["metrics"].keys())
        labels = [k for k, _ in items]
        ax.bar(x, y, color=spec.line_color)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=30, ha="right")
    else:
        ax.plot(x, y, color=spec.line_color)

    fig.tight_layout()

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=spec.dpi, facecolor="white", edgecolor="white", metadata={})
    plt.close(fig)
    buf.seek(0)

    try:
        from PIL import Image
    except Exception:
        out_path.write_bytes(buf.getvalue())
        return out_path

    im = Image.open(buf)
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGBA")
    out_buf = BytesIO()
    im.save(out_buf, format="PNG", optimize=False, compress_level=6)
    out_path.write_bytes(out_buf.getvalue())
    return out_path
def plot_from_results_json(
    results_json_path: Union[str, Path],
    out_png_path: Union[str, Path],
    *,
    spec: Optional[PlotSpec] = None,
) -> Path:
    results_json_path = Path(results_json_path)
    results = json.loads(results_json_path.read_text(encoding="utf-8"))
    if not isinstance(results, dict):
        raise ValueError("results.json must contain a top-level JSON object.")
    return save_figure_png(results, out_png_path, spec=spec)


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    import json as _json

    p = argparse.ArgumentParser(description="Deterministically generate a figure.png from results.json")
    p.add_argument("--results", required=True, help="Path to results.json")
    p.add_argument("--out", required=True, help="Path to write figure.png")
    p.add_argument("--seed", type=int, default=0, help="RNG seed for deterministic plotting")
    p.add_argument("--width", type=float, default=6.4, help="Figure width (inches)")
    p.add_argument("--height", type=float, default=4.0, help="Figure height (inches)")
    p.add_argument("--dpi", type=int, default=100, help="Figure DPI")
    ns = p.parse_args(argv)

    spec = PlotSpec(width_in=ns.width, height_in=ns.height, dpi=ns.dpi, seed=ns.seed)
    plot_from_results_json(ns.results, ns.out, spec=spec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
