"""Convention-driven plotting configuration utilities.

This module provides small, reusable helpers for Matplotlib styling via
themes, rcParams, figure sizing, colormaps, and safe serialization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Tuple, Union

Json = Dict[str, Any]
def _import_mpl():
    try:
        import matplotlib as mpl  # type: ignore
        import matplotlib.pyplot as plt  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "matplotlib is required for plotting configuration utilities"
        ) from e
    return mpl, plt


def _deep_merge(a: Mapping[str, Any], b: Mapping[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = dict(a)
    for k, v in b.items():
        if isinstance(v, Mapping) and isinstance(out.get(k), Mapping):
            out[k] = _deep_merge(out[k], v)  # type: ignore[arg-type]
        else:
            out[k] = v
    return out
_THEMES: Dict[str, Json] = {
    "default": {
        "style": None,
        "cmap": None,
        "rc": {
            "figure.dpi": 120,
            "savefig.dpi": 200,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "legend.frameon": False,
            "font.size": 11,
        },
    },
    "paper": {
        "style": "seaborn-v0_8-whitegrid",
        "cmap": "viridis",
        "rc": {
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "lines.linewidth": 1.6,
        },
    },
    "dark": {
        "style": "dark_background",
        "cmap": "magma",
        "rc": {"axes.grid": False, "text.color": "0.92", "axes.labelcolor": "0.92"},
    },
}
def available_themes() -> Tuple[str, ...]:
    return tuple(sorted(_THEMES))


def theme_dict(name: str) -> Json:
    if name not in _THEMES:
        raise KeyError(f"Unknown theme '{name}'. Available: {', '.join(available_themes())}")
    return dict(_THEMES[name])
@dataclass(frozen=True)
class PlotConfig:
    """Reusable plotting configuration.

    - theme: selects a base theme (style + rc defaults)
    - style: Matplotlib style sheet override (None keeps theme style)
    - rc: rcParams override merged on top of theme rc
    - figsize: default figure size in inches (width, height)
    - dpi: default figure DPI (applied to rcParams['figure.dpi'])
    - cmap: default colormap (None keeps theme cmap)
    - savefig: extra savefig.* rcParams overrides (e.g. bbox_inches)
    """

    theme: str = "default"
    style: Optional[str] = None
    rc: Dict[str, Any] = field(default_factory=dict)
    figsize: Optional[Tuple[float, float]] = None
    dpi: Optional[int] = None
    cmap: Optional[str] = None
    savefig: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Json:
        return {
            "theme": self.theme,
            "style": self.style,
            "rc": dict(self.rc),
            "figsize": list(self.figsize) if self.figsize else None,
            "dpi": self.dpi,
            "cmap": self.cmap,
            "savefig": dict(self.savefig),
        }

    @staticmethod
    def from_dict(d: Mapping[str, Any]) -> "PlotConfig":
        fs = d.get("figsize")
        figsize = tuple(fs) if isinstance(fs, (list, tuple)) and len(fs) == 2 else None
        return PlotConfig(
            theme=str(d.get("theme") or "default"),
            style=d.get("style"),
            rc=dict(d.get("rc") or {}),
            figsize=figsize,  # type: ignore[arg-type]
            dpi=d.get("dpi"),
            cmap=d.get("cmap"),
            savefig=dict(d.get("savefig") or {}),
        )
def resolved_rcparams(cfg: Union[PlotConfig, Mapping[str, Any]]) -> Dict[str, Any]:
    pc = cfg if isinstance(cfg, PlotConfig) else PlotConfig.from_dict(cfg)
    td = theme_dict(pc.theme)
    rc = _deep_merge(td.get("rc", {}), pc.rc)
    if pc.dpi is not None:
        rc["figure.dpi"] = int(pc.dpi)
    for k, v in (pc.savefig or {}).items():
        if not str(k).startswith("savefig."):
            rc[f"savefig.{k}"] = v
        else:
            rc[str(k)] = v
    if pc.figsize is not None:
        rc["figure.figsize"] = tuple(pc.figsize)
    return rc


def apply_plot_config(cfg: Union[PlotConfig, Mapping[str, Any]], *, set_global: bool = True) -> Dict[str, Any]:
    """Apply plotting config.

    If set_global=True (default), updates Matplotlib global state (style + rcParams + default cmap).
    Returns the resolved rcParams dict that was applied (or would be applied).
    """
    pc = cfg if isinstance(cfg, PlotConfig) else PlotConfig.from_dict(cfg)
    td = theme_dict(pc.theme)
    style = pc.style if pc.style is not None else td.get("style")
    cmap = pc.cmap if pc.cmap is not None else td.get("cmap")
    rc = resolved_rcparams(pc)
    if set_global:
        mpl, plt = _import_mpl()
        if style:
            try:
                plt.style.use(style)
            except Exception:
                mpl.style.use(style)  # type: ignore[attr-defined]
        mpl.rcParams.update(rc)
        if cmap:
            try:
                plt.set_cmap(cmap)
            except Exception:
                mpl.rcParams["image.cmap"] = cmap
    return rc


def mpl_rc_context(cfg: Union[PlotConfig, Mapping[str, Any]]):
    """Return a Matplotlib rc_context configured for cfg (context-manager)."""
    mpl, _ = _import_mpl()
    rc = resolved_rcparams(cfg)
    return mpl.rc_context(rc=rc)
__all__ = [
    "PlotConfig",
    "available_themes",
    "theme_dict",
    "resolved_rcparams",
    "apply_plot_config",
    "mpl_rc_context",
]
