# Reusable plotting helpers for experiment outputs.
# Designed to be dependency-light: Matplotlib/Seaborn are imported lazily.

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple, Union


def _import_matplotlib():
    try:
        import matplotlib as mpl  # type: ignore
        import matplotlib.pyplot as plt  # type: ignore
    except Exception as e:  # pragma: no cover
        raise ImportError(
            "Matplotlib is required for plotting utilities. "
            "Install with `pip install matplotlib`."
        ) from e
    return mpl, plt


def _import_seaborn():
    try:
        import seaborn as sns  # type: ignore
    except Exception:
        return None
    return sns


_DEFAULT_RC: Dict[str, Any] = {
    "figure.dpi": 120,
    "savefig.dpi": 150,
    "font.size": 11,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "legend.frameon": False,
}
@contextmanager
def plot_style(
    *,
    use_seaborn: bool = True,
    rc: Optional[Mapping[str, Any]] = None,
    palette: Optional[Union[str, Sequence[Any]]] = "deep",
):
    '''Context manager applying a consistent plotting style.

    Works with Matplotlib alone; if Seaborn is available, a nicer theme is applied.
    '''
    mpl, _ = _import_matplotlib()
    merged = dict(_DEFAULT_RC)
    if rc:
        merged.update(dict(rc))

    sns = _import_seaborn() if use_seaborn else None
    if sns is not None:
        sns.set_theme(context="notebook", style="whitegrid", palette=palette)

    with mpl.rc_context(rc=merged):
        yield

    if sns is not None:
        sns.reset_defaults()
def ensure_ax(ax=None, *, figsize: Tuple[float, float] = (6.4, 4.0)):
    '''Return (fig, ax), creating them if needed.'''
    _, plt = _import_matplotlib()
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
        return fig, ax
    return ax.figure, ax


def save_figure(
    fig,
    path: Union[str, Path],
    *,
    tight: bool = True,
    dpi: Optional[int] = None,
    transparent: bool = False,
    metadata: Optional[Mapping[str, str]] = None,
):
    '''Save a Matplotlib figure with sensible defaults and safe path handling.'''
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    kwargs: Dict[str, Any] = {"transparent": transparent}
    if dpi is not None:
        kwargs["dpi"] = dpi
    if metadata:
        kwargs["metadata"] = dict(metadata)
    if tight:
        kwargs["bbox_inches"] = "tight"
    fig.savefig(str(p), **kwargs)
    return p
def plot_metric_curve(
    records: Sequence[Mapping[str, Any]],
    *,
    x: str = "step",
    y: str = "value",
    hue: Optional[str] = "run",
    ax=None,
    title: Optional[str] = None,
    xlabel: Optional[str] = None,
    ylabel: Optional[str] = None,
    legend: bool = True,
    use_seaborn: bool = True,
):
    '''Plot a metric curve from a list of dict records.

    Expected keys per record: x, y, and optionally hue (e.g., run id / seed).
    This avoids a hard dependency on pandas while still being convenient.
    '''
    _, plt = _import_matplotlib()
    sns = _import_seaborn() if use_seaborn else None
    fig, ax = ensure_ax(ax)

    if sns is not None:
        sns.lineplot(
            data=list(records),
            x=x,
            y=y,
            hue=hue if hue else None,
            ax=ax,
            errorbar=None,
        )
    else:
        if hue:
            groups: Dict[Any, list] = {}
            for r in records:
                groups.setdefault(r.get(hue), []).append(r)
            for k, rows in groups.items():
                xs = [rr.get(x) for rr in rows]
                ys = [rr.get(y) for rr in rows]
                ax.plot(xs, ys, label=str(k))
        else:
            xs = [r.get(x) for r in records]
            ys = [r.get(y) for r in records]
            ax.plot(xs, ys)

    ax.set_title(title or "")
    ax.set_xlabel(xlabel or x)
    ax.set_ylabel(ylabel or y)
    if legend and hue:
        ax.legend(title=hue)
    elif ax.get_legend() is not None:
        ax.get_legend().remove()
    plt.tight_layout()
    return fig, ax
def plot_summary_bar(
    values: Mapping[str, float],
    *,
    ax=None,
    title: Optional[str] = None,
    xlabel: str = "",
    ylabel: str = "value",
    sort: bool = True,
    rotation: int = 30,
    use_seaborn: bool = True,
):
    '''Plot an aggregated summary as a bar chart (e.g., final scores by method).'''
    _, plt = _import_matplotlib()
    sns = _import_seaborn() if use_seaborn else None
    fig, ax = ensure_ax(ax, figsize=(7.2, 4.0))

    items = list(values.items())
    if sort:
        items.sort(key=lambda kv: kv[1], reverse=True)
    labels, ys = zip(*items) if items else ([], [])

    if sns is not None:
        sns.barplot(x=list(labels), y=list(ys), ax=ax)
    else:
        ax.bar(list(labels), list(ys))

    ax.set_title(title or "")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=rotation, ha="right")
    plt.tight_layout()
    return fig, ax
