"""Determinism helpers: global seed pinning + deterministic matplotlib defaults.

This module centralizes reproducibility controls across Python, numpy, and torch
(if installed), and enforces stable matplotlib rendering parameters.
"""

from __future__ import annotations

import os
import random
from dataclasses import dataclass
from typing import Any, Optional, Tuple
def _try_import(name: str):
    try:
        return __import__(name)
    except Exception:
        return None


def set_global_seed(seed: int, *, deterministic_torch: bool = True) -> dict:
    """Set seeds across common libraries; returns a summary dict."""
    seed = int(seed)
    os.environ.setdefault("PYTHONHASHSEED", str(seed))
    random.seed(seed)

    summary = {"seed": seed, "pythonhashseed": os.environ.get("PYTHONHASHSEED")}

    np = _try_import("numpy")
    if np is not None:
        try:
            np.random.seed(seed)
            summary["numpy"] = True
        except Exception:
            summary["numpy"] = False
    else:
        summary["numpy"] = None

    torch = _try_import("torch")
    if torch is not None:
        try:
            torch.manual_seed(seed)
            if getattr(torch, "cuda", None) is not None and torch.cuda.is_available():
                torch.cuda.manual_seed_all(seed)

            if deterministic_torch:
                os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
                try:
                    torch.use_deterministic_algorithms(True)
                except Exception:
                    pass
                try:
                    torch.backends.cudnn.deterministic = True
                    torch.backends.cudnn.benchmark = False
                except Exception:
                    pass
                try:
                    torch.backends.cuda.matmul.allow_tf32 = False
                except Exception:
                    pass
                try:
                    torch.backends.cudnn.allow_tf32 = False
                except Exception:
                    pass

            summary["torch"] = True
            summary["torch_deterministic"] = bool(deterministic_torch)
        except Exception:
            summary["torch"] = False
    else:
        summary["torch"] = None

    return summary
@dataclass(frozen=True)
class MatplotlibDeterminism:
    backend: str = "Agg"
    dpi: int = 150
    figsize: Tuple[float, float] = (6.4, 4.8)
    font_family: str = "DejaVu Sans"
    font_size: int = 10
    linewidth: float = 1.25
    antialiased: bool = True
    svg_hashsalt: str = "0"


def set_matplotlib_determinism(cfg: Optional[MatplotlibDeterminism] = None) -> dict:
    """Apply stable matplotlib defaults for deterministic figure output."""
    cfg = cfg or MatplotlibDeterminism()

    mpl = _try_import("matplotlib")
    if mpl is None:
        return {"matplotlib": None}

    try:
        try:
            mpl.use(cfg.backend, force=True)
        except Exception:
            pass

        rc = mpl.rcParams
        rc["figure.dpi"] = cfg.dpi
        rc["savefig.dpi"] = cfg.dpi
        rc["figure.figsize"] = list(cfg.figsize)
        rc["savefig.bbox"] = "tight"
        rc["savefig.pad_inches"] = 0.1

        rc["font.family"] = cfg.font_family
        rc["font.size"] = cfg.font_size
        rc["axes.linewidth"] = cfg.linewidth
        rc["lines.linewidth"] = cfg.linewidth
        rc["lines.antialiased"] = cfg.antialiased
        rc["patch.antialiased"] = cfg.antialiased

        rc["text.usetex"] = False
        rc["path.simplify"] = False
        rc["path.simplify_threshold"] = 0.0

        # Stable vector output (avoid random-ish identifiers)
        rc["svg.hashsalt"] = cfg.svg_hashsalt
        rc["pdf.fonttype"] = 42
        rc["ps.fonttype"] = 42

        # Avoid locale-dependent formatting surprises
        rc["axes.formatter.use_locale"] = False

        return {"matplotlib": True, "backend": str(mpl.get_backend()), "dpi": cfg.dpi}
    except Exception:
        return {"matplotlib": False}
def apply_determinism(
    seed: int,
    *,
    deterministic_torch: bool = True,
    mpl: bool = True,
    mpl_cfg: Optional[MatplotlibDeterminism] = None,
) -> dict:
    """Convenience entrypoint to pin RNG and plotting determinism."""
    out: dict[str, Any] = {"seed": int(seed)}
    out["rng"] = set_global_seed(seed, deterministic_torch=deterministic_torch)
    out["plotting"] = set_matplotlib_determinism(mpl_cfg) if mpl else {"matplotlib": None}
    return out
