from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Optional, Tuple
import numpy as np
@dataclass
class MetaResult:
    model: str
    k: int
    yi: np.ndarray
    vi: np.ndarray
    weights: np.ndarray
    pooled: float
    se: float
    ci_low: float
    ci_high: float
    Q: float
    df: int
    p_Q: float
    I2: float
    tau2: float

    def as_dict(self) -> dict:
        return {
            "model": self.model,
            "k": int(self.k),
            "pooled": float(self.pooled),
            "se": float(self.se),
            "ci_low": float(self.ci_low),
            "ci_high": float(self.ci_high),
            "Q": float(self.Q),
            "df": int(self.df),
            "p_Q": float(self.p_Q),
            "I2": float(self.I2),
            "tau2": float(self.tau2),
        }
def _as_1d(a: Iterable[float]) -> np.ndarray:
    x = np.asarray(list(a), dtype=float)
    if x.ndim != 1:
        raise ValueError("Input must be 1D.")
    return x

def zcrit(alpha: float = 0.05) -> float:
    try:
        from scipy.stats import norm
        return float(norm.ppf(1 - alpha / 2))
    except Exception:
        return 1.959963984540054

def pvalue_chi2(Q: float, df: int) -> float:
    if df <= 0:
        return float("nan")
    try:
        from scipy.stats import chi2
        return float(chi2.sf(Q, df))
    except Exception:
        return float("nan")
def effect_log_rr(e_t: float, n_t: float, e_c: float, n_c: float, cc: float = 0.5) -> Tuple[float, float]:
    e_t, n_t, e_c, n_c = map(float, (e_t, n_t, e_c, n_c))
    if any(v <= 0 for v in (n_t, n_c)):
        raise ValueError("Group totals must be positive.")
    ne_t, ne_c = n_t - e_t, n_c - e_c
    if min(e_t, ne_t, e_c, ne_c) <= 0:
        e_t, ne_t, e_c, ne_c = e_t + cc, ne_t + cc, e_c + cc, ne_c + cc
    rr = (e_t / (e_t + ne_t)) / (e_c / (e_c + ne_c))
    yi = float(np.log(rr))
    vi = float(1 / e_t - 1 / (e_t + ne_t) + 1 / e_c - 1 / (e_c + ne_c))
    return yi, vi

def effect_md(mean_t: float, sd_t: float, n_t: float, mean_c: float, sd_c: float, n_c: float) -> Tuple[float, float]:
    mean_t, sd_t, n_t, mean_c, sd_c, n_c = map(float, (mean_t, sd_t, n_t, mean_c, sd_c, n_c))
    if n_t <= 0 or n_c <= 0:
        raise ValueError("Sample sizes must be positive.")
    yi = mean_t - mean_c
    vi = (sd_t ** 2) / n_t + (sd_c ** 2) / n_c
    return float(yi), float(vi)
def heterogeneity(yi: Iterable[float], vi: Iterable[float]) -> Tuple[float, int, float, float]:
    y, v = _as_1d(yi), _as_1d(vi)
    if len(y) != len(v) or len(y) == 0:
        raise ValueError("yi and vi must be same nonzero length.")
    w = 1.0 / v
    mu = float(np.sum(w * y) / np.sum(w))
    Q = float(np.sum(w * (y - mu) ** 2))
    df = int(len(y) - 1)
    p_Q = pvalue_chi2(Q, df)
    I2 = float(max(0.0, (Q - df) / Q) * 100.0) if Q > 0 and df > 0 else 0.0
    return Q, df, p_Q, I2

def tau2_dl(yi: Iterable[float], vi: Iterable[float]) -> float:
    y, v = _as_1d(yi), _as_1d(vi)
    w = 1.0 / v
    Q, df, _, _ = heterogeneity(y, v)
    c = float(np.sum(w) - (np.sum(w ** 2) / np.sum(w)))
    if c <= 0 or df <= 0:
        return 0.0
    return float(max(0.0, (Q - df) / c))
def pool_fixed(yi: Iterable[float], vi: Iterable[float], alpha: float = 0.05) -> MetaResult:
    y, v = _as_1d(yi), _as_1d(vi)
    w = 1.0 / v
    pooled = float(np.sum(w * y) / np.sum(w))
    se = float(np.sqrt(1.0 / np.sum(w)))
    z = zcrit(alpha)
    ci_low, ci_high = pooled - z * se, pooled + z * se
    Q, df, p_Q, I2 = heterogeneity(y, v)
    return MetaResult("fixed", len(y), y, v, w, pooled, se, ci_low, ci_high, Q, df, p_Q, I2, 0.0)

def pool_random(yi: Iterable[float], vi: Iterable[float], alpha: float = 0.05) -> MetaResult:
    y, v = _as_1d(yi), _as_1d(vi)
    t2 = tau2_dl(y, v)
    w = 1.0 / (v + t2)
    pooled = float(np.sum(w * y) / np.sum(w))
    se = float(np.sqrt(1.0 / np.sum(w)))
    z = zcrit(alpha)
    ci_low, ci_high = pooled - z * se, pooled + z * se
    Q, df, p_Q, I2 = heterogeneity(y, v)
    return MetaResult("random", len(y), y, v, w, pooled, se, ci_low, ci_high, Q, df, p_Q, I2, float(t2))
def _maybe_exp(x: np.ndarray, log_scale: bool) -> np.ndarray:
    return np.exp(x) if log_scale else x

def forest_plot(study_labels: Iterable[str],
                yi: Iterable[float],
                vi: Iterable[float],
                pooled: Optional[MetaResult] = None,
                out_path: Optional[str] = None,
                title: str = "Forest plot",
                effect_label: str = "Effect",
                log_scale: bool = False,
                alpha: float = 0.05,
                figsize: Tuple[float, float] = (7.0, 4.5)) -> str:
    labels = list(study_labels)
    y, v = _as_1d(yi), _as_1d(vi)
    if len(labels) != len(y):
        raise ValueError("study_labels must match yi length.")
    import matplotlib.pyplot as plt

    z = zcrit(alpha)
    se = np.sqrt(v)
    lo, hi = y - z * se, y + z * se
    y_plot, lo_plot, hi_plot = _maybe_exp(y, log_scale), _maybe_exp(lo, log_scale), _maybe_exp(hi, log_scale)

    k = len(y)
    fig_h = max(figsize[1], 0.45 * (k + (1 if pooled else 0)) + 1.2)
    fig, ax = plt.subplots(figsize=(figsize[0], fig_h))
    ypos = np.arange(k, 0, -1)

    ax.hlines(ypos, lo_plot, hi_plot, color="black", lw=1)
    ax.plot(y_plot, ypos, "s", color="black", ms=5)

    if pooled is not None:
        p_lo, p_hi = pooled.ci_low, pooled.ci_high
        p_mu = pooled.pooled
        p_mu, p_lo, p_hi = _maybe_exp(np.array([p_mu, p_lo, p_hi]), log_scale)
        ax.hlines(0, p_lo, p_hi, color="tab:blue", lw=2)
        ax.plot(p_mu, 0, "D", color="tab:blue", ms=7)

    ax.set_yticks(list(ypos) + ([0] if pooled else []))
    ax.set_yticklabels(labels + (["Pooled"] if pooled else []))
    ax.set_xlabel(effect_label + (" (exp scale)" if log_scale else ""))
    ax.set_title(title)
    ax.axvline(1.0 if log_scale else 0.0, color="grey", lw=1, ls="--", alpha=0.8)
    ax.set_ylim(-1, k + 1)
    ax.grid(axis="x", alpha=0.25)

    fig.tight_layout()
    if out_path:
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=200, bbox_inches="tight")
        plt.close(fig)
        return str(out)
    return 
def summary_rows(result: MetaResult, label: str = "") -> list[dict]:
    d = result.as_dict()
    d["label"] = label or result.model
    return [d]

def to_dataframe(rows: list[dict]):
    try:
        import pandas as pd
    except Exception as e:
        raise ImportError("pandas is required to build summary tables.") from e
    cols = ["label","model","k","pooled","se","ci_low","ci_high","Q","df","p_Q","I2","tau2"]
    df = pd.DataFrame(rows)
    for c in cols:
        if c not in df.columns:
            df[c] = np.nan
    return df[cols]
