"""Plotting helpers for notebook-ready EV conversion comparisons.

Provides consistent matplotlib styling, common plots (TCO breakdown,
sensitivity curves, utilization curves, and drive-cycle comparisons),
and lightweight summary table formatting.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt


__all__ = [
    "PlotStyle",
    "set_plot_style",
    "make_summary_table",
    "plot_tco_breakdown",
    "plot_energy_sensitivity",
    "plot_utilization_curves",
    "plot_cycle_comparison",
]


@dataclass(frozen=True)
class PlotStyle:
    figsize: Tuple[float, float] = (9.0, 4.8)
    dpi: int = 120
    grid: bool = True
    title_size: int = 12
    label_size: int = 10
    tick_size: int = 9
    legend_size: int = 9
    palette: Tuple[str, ...] = (
        "#4C78A8", "#F58518", "#54A24B", "#E45756", "#72B7B2", "#B279A2", "#FF9DA6"
    )


def set_plot_style(style: PlotStyle = PlotStyle()) -> None:
    mpl.rcParams.update(
        {
            "figure.dpi": style.dpi,
            "figure.figsize": style.figsize,
            "axes.titlesize": style.title_size,
            "axes.labelsize": style.label_size,
            "xtick.labelsize": style.tick_size,
            "ytick.labelsize": style.tick_size,
            "legend.fontsize": style.legend_size,
            "axes.grid": style.grid,
            "grid.alpha": 0.25,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    mpl.rcParams["axes.prop_cycle"] = mpl.cycler(color=list(style.palette))


def _as_list(x: Optional[Sequence[str]]) -> list:
    if x is None:
        return []
    return list(x)


def _ensure_df(df) -> pd.DataFrame:
    if isinstance(df, pd.DataFrame):
        return df
    return pd.DataFrame(df)


def make_summary_table(
    df,
    index: Sequence[str] = ("segment", "powertrain", "cycle"),
    columns: Optional[Sequence[str]] = None,
    sort: bool = True,
    round_to: int = 3,
) -> pd.DataFrame:
    d = _ensure_df(df).copy()
    idx = [c for c in index if c in d.columns]
    if not idx:
        raise ValueError("No index columns found in df for summary table.")
    if columns is None:
        columns = [c for c in d.columns if c not in idx]
    cols = [c for c in columns if c in d.columns]
    out = d[idx + cols].copy()
    if sort:
        out = out.sort_values(idx)
    for c in cols:
        if pd.api.types.is_numeric_dtype(out[c]):
            out[c] = out[c].round(round_to)
    return out.set_index(idx)
def _currency_axis(ax, symbol: str = "$") -> None:
    ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: f"{symbol}{v:,.0f}"))


def plot_tco_breakdown(
    df,
    scenario_col: str = "powertrain",
    components: Optional[Sequence[str]] = None,
    title: str = "TCO breakdown",
    y_label: str = "Total cost (lifetime)",
    currency: bool = True,
    ax=None,
):
    d = _ensure_df(df).copy()
    if scenario_col not in d.columns:
        raise ValueError(f"scenario_col '{scenario_col}' not in df.")
    if components is None:
        components = [c for c in d.columns if c != scenario_col and pd.api.types.is_numeric_dtype(d[c])]
    components = [c for c in components if c in d.columns]
    if not components:
        raise ValueError("No cost components found to plot.")
    d = d[[scenario_col] + components].groupby(scenario_col, as_index=False).sum()

    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure

    x = np.arange(len(d))
    bottoms = np.zeros(len(d))
    for comp in components:
        vals = d[comp].to_numpy(dtype=float)
        ax.bar(x, vals, bottom=bottoms, label=str(comp))
        bottoms = bottoms + vals

    ax.set_xticks(x, d[scenario_col].astype(str).tolist(), rotation=0)
    ax.set_title(title)
    ax.set_ylabel(y_label)
    ax.legend(ncols=min(3, len(components)), frameon=False)
    if currency:
        _currency_axis(ax)
    ax.margins(x=0.05)
    return fig, ax


def plot_energy_sensitivity(
    df,
    x: str = "energy_price",
    y: str = "tco_per_mile",
    group: str = "powertrain",
    title: str = "Energy price sensitivity",
    x_label: Optional[str] = None,
    y_label: Optional[str] = None,
    ax=None,
):
    d = _ensure_df(df).copy()
    for col in (x, y, group):
        if col not in d.columns:
            raise ValueError(f"'{col}' not in df.")
    d = d.sort_values([group, x])

    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure

    for g, sub in d.groupby(group):
        ax.plot(sub[x].to_numpy(), sub[y].to_numpy(), marker="o", linewidth=2, label=str(g))

    ax.set_title(title)
    ax.set_xlabel(x_label or x.replace("_", " ").title())
    ax.set_ylabel(y_label or y.replace("_", " ").title())
    ax.legend(frameon=False)
    return fig, ax
def plot_utilization_curves(
    df,
    x: str = "annual_miles",
    y: str = "tco_per_mile",
    group: str = "powertrain",
    title: str = "Utilization vs TCO",
    ax=None,
):
    d = _ensure_df(df).copy()
    for col in (x, y, group):
        if col not in d.columns:
            raise ValueError(f"'{col}' not in df.")
    d = d.sort_values([group, x])

    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure

    for g, sub in d.groupby(group):
        ax.plot(sub[x].to_numpy(), sub[y].to_numpy(), marker=None, linewidth=2, label=str(g))

    ax.set_title(title)
    ax.set_xlabel(x.replace("_", " ").title())
    ax.set_ylabel(y.replace("_", " ").title())
    ax.legend(frameon=False)
    ax.margins(x=0.02)
    return fig, ax


def plot_cycle_comparison(
    df,
    cycle_col: str = "cycle",
    metric: str = "energy_per_mile",
    group: str = "powertrain",
    title: Optional[str] = None,
    ax=None,
):
    d = _ensure_df(df).copy()
    for col in (cycle_col, metric, group):
        if col not in d.columns:
            raise ValueError(f"'{col}' not in df.")
    pivot = (
        d[[cycle_col, group, metric]]
        .dropna()
        .groupby([cycle_col, group], as_index=False)[metric]
        .mean()
        .pivot(index=cycle_col, columns=group, values=metric)
    )
    pivot = pivot.loc[pivot.index.astype(str).sort_values().index] if len(pivot) else pivot

    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure

    cycles = pivot.index.astype(str).tolist()
    groups = pivot.columns.astype(str).tolist()
    x = np.arange(len(cycles))
    width = 0.8 / max(1, len(groups))

    for i, g in enumerate(groups):
        vals = pivot[g].to_numpy(dtype=float)
        ax.bar(x + (i - (len(groups) - 1) / 2) * width, vals, width=width, label=str(g))

    ax.set_xticks(x, cycles)
    ax.set_xlabel(cycle_col.replace("_", " ").title())
    ax.set_ylabel(metric.replace("_", " ").title())
    ax.set_title(title or f"Cycle comparison: {metric.replace('_',' ')}")
    ax.legend(frameon=False)
    ax.margins(x=0.05)
    return fig, ax
