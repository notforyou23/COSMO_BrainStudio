from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Tuple

__all__ = [
    "STYLE_PRESETS",
    "PlotOptions",
    "default_plot_options",
    "merge_plot_options",
    "validate_plot_options",
    "to_mpl_line_kwargs",
    "to_mpl_figure_kwargs",
    "to_mpl_axes_kwargs",
]


STYLE_PRESETS: Dict[str, Dict[str, Any]] = {
    "default": {
        "figure": {"figsize": (7.0, 4.0), "dpi": 120},
        "axes": {"grid": True, "grid_alpha": 0.25, "title": None, "xlabel": None, "ylabel": None},
        "line": {"color": None, "linewidth": 2.0, "linestyle": "-", "marker": None, "markersize": 5.0, "alpha": 1.0},
        "legend": {"show": True, "loc": "best"},
    },
    "paper": {
        "figure": {"figsize": (6.0, 3.5), "dpi": 200},
        "axes": {"grid": True, "grid_alpha": 0.2},
        "line": {"linewidth": 1.5, "markersize": 4.0},
        "legend": {"show": True, "loc": "best"},
    },
    "presentation": {
        "figure": {"figsize": (9.0, 5.0), "dpi": 120},
        "axes": {"grid": True, "grid_alpha": 0.25},
        "line": {"linewidth": 3.0, "markersize": 7.0},
        "legend": {"show": True, "loc": "best"},
    },
}


def _deep_merge(base: Dict[str, Any], override: Mapping[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, Mapping) and isinstance(out.get(k), Mapping):
            out[k] = _deep_merge(dict(out[k]), v)
        else:
            out[k] = v
    return out


def _as_tuple2(v: Any, *, name: str) -> Optional[Tuple[float, float]]:
    if v is None:
        return None
    if isinstance(v, (list, tuple)) and len(v) == 2:
        return (float(v[0]), float(v[1]))
    raise ValueError(f"{name} must be a 2-tuple (min, max) or None")
@dataclass(frozen=True)
class PlotOptions:
    figure: Dict[str, Any]
    axes: Dict[str, Any]
    line: Dict[str, Any]
    legend: Dict[str, Any]

    def as_dict(self) -> Dict[str, Any]:
        return {"figure": dict(self.figure), "axes": dict(self.axes), "line": dict(self.line), "legend": dict(self.legend)}


def default_plot_options(preset: str = "default", **overrides: Any) -> PlotOptions:
    if preset not in STYLE_PRESETS:
        raise KeyError(f"Unknown plot preset: {preset!r}. Available: {sorted(STYLE_PRESETS)}")
    base = _deep_merge({}, STYLE_PRESETS[preset])
    if overrides:
        base = _deep_merge(base, overrides)
    return validate_plot_options(base)


def merge_plot_options(base: Mapping[str, Any], override: Mapping[str, Any]) -> PlotOptions:
    return validate_plot_options(_deep_merge(dict(base), override))


def validate_plot_options(opts: Mapping[str, Any]) -> PlotOptions:
    if not isinstance(opts, Mapping):
        raise TypeError("plot options must be a mapping")

    fig = dict(opts.get("figure") or {})
    axes = dict(opts.get("axes") or {})
    line = dict(opts.get("line") or {})
    legend = dict(opts.get("legend") or {})

    if "figsize" in fig:
        fs = fig["figsize"]
        if not (isinstance(fs, (list, tuple)) and len(fs) == 2):
            raise ValueError("figure.figsize must be a 2-tuple (width, height)")
        fig["figsize"] = (float(fs[0]), float(fs[1]))
    if "dpi" in fig and fig["dpi"] is not None:
        fig["dpi"] = int(fig["dpi"])
        if fig["dpi"] <= 0:
            raise ValueError("figure.dpi must be > 0")

    for b in ("grid",):
        if b in axes and axes[b] is not None:
            axes[b] = bool(axes[b])
    if "grid_alpha" in axes and axes["grid_alpha"] is not None:
        ga = float(axes["grid_alpha"])
        if not (0.0 <= ga <= 1.0):
            raise ValueError("axes.grid_alpha must be within [0, 1]")
        axes["grid_alpha"] = ga

    for lim in ("xlim", "ylim"):
        if lim in axes:
            axes[lim] = _as_tuple2(axes[lim], name=f"axes.{lim}")
    for sc in ("xscale", "yscale"):
        if sc in axes and axes[sc] is not None:
            axes[sc] = str(axes[sc])

    for key in ("linewidth", "markersize", "alpha"):
        if key in line and line[key] is not None:
            line[key] = float(line[key])
    if "alpha" in line and line["alpha"] is not None and not (0.0 <= line["alpha"] <= 1.0):
        raise ValueError("line.alpha must be within [0, 1]")
    for key in ("color", "linestyle", "marker"):
        if key in line and line[key] is not None:
            line[key] = str(line[key])

    if "show" in legend and legend["show"] is not None:
        legend["show"] = bool(legend["show"])
    if "loc" in legend and legend["loc"] is not None:
        legend["loc"] = str(legend["loc"])

    return PlotOptions(figure=fig, axes=axes, line=line, legend=legend)
def to_mpl_line_kwargs(opts: Mapping[str, Any] | PlotOptions) -> Dict[str, Any]:
    d = opts.as_dict() if isinstance(opts, PlotOptions) else dict(opts)
    line = dict(d.get("line") or {})
    out: Dict[str, Any] = {}
    mapping = {
        "color": "color",
        "linewidth": "linewidth",
        "linestyle": "linestyle",
        "marker": "marker",
        "markersize": "markersize",
        "alpha": "alpha",
    }
    for src, dst in mapping.items():
        v = line.get(src)
        if v is not None:
            out[dst] = v
    return out


def to_mpl_figure_kwargs(opts: Mapping[str, Any] | PlotOptions) -> Dict[str, Any]:
    d = opts.as_dict() if isinstance(opts, PlotOptions) else dict(opts)
    fig = dict(d.get("figure") or {})
    out: Dict[str, Any] = {}
    for k in ("figsize", "dpi"):
        if fig.get(k) is not None:
            out[k] = fig[k]
    return out


def to_mpl_axes_kwargs(opts: Mapping[str, Any] | PlotOptions) -> Dict[str, Any]:
    d = opts.as_dict() if isinstance(opts, PlotOptions) else dict(opts)
    axes = dict(d.get("axes") or {})
    out: Dict[str, Any] = {}
    for k in ("title", "xlabel", "ylabel", "xlim", "ylim", "xscale", "yscale"):
        if axes.get(k) is not None:
            out[k] = axes[k]
    grid = axes.get("grid")
    if grid is not None:
        out["_grid"] = bool(grid)
        if axes.get("grid_alpha") is not None:
            out["_grid_alpha"] = axes["grid_alpha"]
    return out
