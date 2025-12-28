from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

import math

try:
    import pandas as pd  # type: ignore
except Exception as e:  # pragma: no cover
    pd = None  # type: ignore

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


Number = Union[int, float]


def _first_existing(df, names: Sequence[str]) -> Optional[str]:
    cols = {str(c).strip().lower(): c for c in df.columns}
    for n in names:
        k = n.strip().lower()
        if k in cols:
            return cols[k]
    return None


def _coerce_float(x) -> float:
    if x is None:
        return float("nan")
    try:
        if isinstance(x, bool):
            return float("nan")
        return float(x)
    except Exception:
        s = str(x).strip()
        if s == "" or s.lower() in {"na", "nan", "none", "null"}:
            return float("nan")
        try:
            return float(s)
        except Exception:
            return float("nan")


def _ensure_dir(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)


def _default_figsize(n_rows: int) -> Tuple[float, float]:
    h = max(2.2, min(0.45 * n_rows + 1.5, 12.0))
    return (8.6, h)


def _compute_ci(effect: float, se: float, z: float = 1.96) -> Tuple[float, float]:
    if not (math.isfinite(effect) and math.isfinite(se) and se > 0):
        return (float("nan"), float("nan"))
    return (effect - z * se, effect + z * se)


def _deterministic_sort(df, label_col: str) -> "pd.DataFrame":
    if "order" in {str(c).strip().lower() for c in df.columns}:
        oc = _first_existing(df, ["order"])
        if oc is not None:
            return df.sort_values(by=[oc, label_col], kind="mergesort").reset_index(drop=True)
    return df.sort_values(by=[label_col], kind="mergesort").reset_index(drop=True)


@dataclass(frozen=True)
class PlotConfig:
    title: str = "Pooled meta-analysis estimates"
    xlabel: str = "Effect"
    null_value: float = 0.0
    dpi: int = 180
    formats: Tuple[str, ...] = ("png",)
    show_values: bool = True
    show_null: bool = True
    xlim: Optional[Tuple[float, float]] = None
    style: str = "default"

    @staticmethod
    def from_dict(d: Optional[Dict]) -> "PlotConfig":
        d = d or {}
        fmts = d.get("formats", d.get("format", ("png",)))
        if isinstance(fmts, str):
            fmts = (fmts,)
        fmts = tuple(str(x).lower().lstrip(".") for x in fmts if str(x).strip())
        xlim = d.get("xlim", None)
        if isinstance(xlim, (list, tuple)) and len(xlim) == 2:
            try:
                xlim = (float(xlim[0]), float(xlim[1]))
            except Exception:
                xlim = None
        else:
            xlim = None
        return PlotConfig(
            title=str(d.get("title", PlotConfig.title)),
            xlabel=str(d.get("xlabel", PlotConfig.xlabel)),
            null_value=float(d.get("null_value", PlotConfig.null_value)),
            dpi=int(d.get("dpi", PlotConfig.dpi)),
            formats=fmts or ("png",),
            show_values=bool(d.get("show_values", PlotConfig.show_values)),
            show_null=bool(d.get("show_null", PlotConfig.show_null)),
            xlim=xlim,
            style=str(d.get("style", PlotConfig.style)),
        )
def forest_plot_from_pooled(
    pooled: "pd.DataFrame",
    out_basepath: Union[str, Path],
    plot_config: Optional[Dict] = None,
) -> List[Path]:
    if pd is None:
        raise RuntimeError("pandas is required for plotting.")
    cfg = PlotConfig.from_dict(plot_config)

    label_col = _first_existing(pooled, ["label", "name", "outcome", "comparison", "model", "effect_type"])
    eff_col = _first_existing(pooled, ["estimate", "effect", "pooled", "theta", "yi"])
    se_col = _first_existing(pooled, ["se", "std_error", "stderr"])
    lo_col = _first_existing(pooled, ["ci_low", "ci_lower", "lower", "lcl"])
    hi_col = _first_existing(pooled, ["ci_high", "ci_upper", "upper", "ucl"])

    if label_col is None:
        label_col = pooled.columns[0]
    if eff_col is None:
        raise ValueError("Pooled results must include an effect/estimate column (e.g., 'estimate').")

    df = pooled.copy()
    df[label_col] = df[label_col].astype(str)
    df = _deterministic_sort(df, label_col)

    eff = df[eff_col].map(_coerce_float).tolist()
    se = df[se_col].map(_coerce_float).tolist() if se_col is not None else [float("nan")] * len(df)
    if lo_col is not None and hi_col is not None:
        lo = df[lo_col].map(_coerce_float).tolist()
        hi = df[hi_col].map(_coerce_float).tolist()
    else:
        lo, hi = [], []
        for e, s in zip(eff, se):
            l, u = _compute_ci(e, s)
            lo.append(l)
            hi.append(u)

    labels = df[label_col].tolist()
    n = len(labels)

    with plt.style.context(cfg.style):
        fig_w, fig_h = _default_figsize(n)
        fig, ax = plt.subplots(figsize=(fig_w, fig_h))
        y = list(range(n))[::-1]

        x_min = min([v for v in lo + eff if math.isfinite(v)] + [cfg.null_value])
        x_max = max([v for v in hi + eff if math.isfinite(v)] + [cfg.null_value])
        pad = 0.08 * (x_max - x_min if x_max > x_min else 1.0)
        auto_xlim = (x_min - pad, x_max + pad)
        xlim = cfg.xlim or auto_xlim

        if cfg.show_null and math.isfinite(cfg.null_value):
            ax.axvline(cfg.null_value, color="0.35", lw=1.0, ls="--", zorder=0)

        for yi, e, l, u in zip(y, eff, lo, hi):
            if not (math.isfinite(e) and math.isfinite(l) and math.isfinite(u)):
                continue
            ax.plot([l, u], [yi, yi], color="0.25", lw=1.4, solid_capstyle="butt", zorder=2)
            ax.scatter([e], [yi], s=32, color="#1f77b4", edgecolor="white", linewidth=0.6, zorder=3)

        ax.set_yticks(y)
        ax.set_yticklabels(labels)
        ax.set_xlabel(cfg.xlabel)
        ax.set_title(cfg.title)
        ax.set_xlim(*xlim)
        ax.grid(axis="x", color="0.9", lw=0.8)
        ax.set_axisbelow(True)

        if cfg.show_values:
            xt = xlim[1]
            x_text = xt - 0.01 * (xlim[1] - xlim[0])
            for yi, e, l, u in zip(y, eff, lo, hi):
                if not (math.isfinite(e) and math.isfinite(l) and math.isfinite(u)):
                    txt = "NA"
                else:
                    txt = f"{e:.3f} [{l:.3f}, {u:.3f}]"
                ax.text(x_text, yi, txt, va="center", ha="right", fontsize=9, color="0.2")

        fig.tight_layout()

        out_base = Path(out_basepath)
        saved: List[Path] = []
        for fmt in cfg.formats:
            fmt = str(fmt).lower().lstrip(".")
            if fmt not in {"png", "pdf"}:
                continue
            out_path = out_base.with_suffix("." + fmt)
            _ensure_dir(out_path)
            fig.savefig(out_path, dpi=cfg.dpi if fmt == "png" else None, bbox_inches="tight")
            saved.append(out_path)

        plt.close(fig)

    return saved


def plot_from_config(
    pooled_results_path: Union[str, Path],
    output_basepath: Union[str, Path],
    config: Optional[Dict] = None,
) -> List[Path]:
    if pd is None:
        raise RuntimeError("pandas is required for plotting.")
    pooled_results_path = Path(pooled_results_path)
    if not pooled_results_path.exists():
        raise FileNotFoundError(str(pooled_results_path))
    df = pd.read_csv(pooled_results_path)
    plot_cfg = (config or {}).get("plot", config or {})
    return forest_plot_from_pooled(df, output_basepath, plot_cfg)
