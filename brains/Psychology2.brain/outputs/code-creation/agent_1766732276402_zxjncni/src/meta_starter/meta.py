"""Core meta-analysis computations (fixed-effect + random-effects).

This module is intentionally small and dependency-light so it can serve as the
compute layer for a minimal, reproducible meta-analysis starter kit.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Iterable, List, Dict, Sequence, Optional, Tuple


Z_95 = 1.959963984540054  # two-sided 95% CI under normal approximation


def _to_list_floats(x: Iterable[float]) -> List[float]:
    out: List[float] = []
    for v in x:
        fv = float(v)
        if fv != fv:
            raise ValueError("NaN encountered in numeric input")
        out.append(fv)
    if not out:
        raise ValueError("Empty numeric input")
    return out


def _check_lengths(y: Sequence[float], v: Sequence[float]) -> None:
    if len(y) != len(v):
        raise ValueError(f"Length mismatch: len(y)={len(y)} len(v)={len(v)}")
    if len(y) < 2:
        raise ValueError("At least 2 studies are required")


def _wmean(y: Sequence[float], w: Sequence[float]) -> float:
    sw = sum(w)
    if sw <= 0:
        raise ValueError("Non-positive total weight")
    return sum(wi * yi for yi, wi in zip(y, w)) / sw


def _pooled_se(w: Sequence[float]) -> float:
    sw = sum(w)
    if sw <= 0:
        raise ValueError("Non-positive total weight")
    return sqrt(1.0 / sw)


def ci_normal(est: float, se: float, z: float = Z_95) -> Tuple[float, float]:
    return (est - z * se, est + z * se)


@dataclass(frozen=True)
class MetaResult:
    model: str  # "fixed" or "random"
    k: int
    est: float
    se: float
    ci_low: float
    ci_high: float
    Q: Optional[float] = None
    df: Optional[int] = None
    tau2: Optional[float] = None
    I2: Optional[float] = None

    def as_row(self) -> Dict[str, float]:
        d: Dict[str, float] = {
            "model": self.model,
            "k": float(self.k),
            "est": self.est,
            "se": self.se,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
        }
        if self.Q is not None:
            d["Q"] = self.Q
        if self.df is not None:
            d["df"] = float(self.df)
        if self.tau2 is not None:
            d["tau2"] = self.tau2
        if self.I2 is not None:
            d["I2_percent"] = self.I2
        return d
def fixed_effect(y: Iterable[float], v: Iterable[float]) -> MetaResult:
    """Inverse-variance fixed-effect pooling.

    Args:
        y: Study effect estimates.
        v: Study variances (SE^2), same length as y.
    """
    yy = _to_list_floats(y)
    vv = _to_list_floats(v)
    _check_lengths(yy, vv)
    if any(vi <= 0 for vi in vv):
        raise ValueError("All variances must be > 0")
    w = [1.0 / vi for vi in vv]
    est = _wmean(yy, w)
    se = _pooled_se(w)
    lo, hi = ci_normal(est, se)
    return MetaResult(model="fixed", k=len(yy), est=est, se=se, ci_low=lo, ci_high=hi)


def heterogeneity_Q(y: Sequence[float], v: Sequence[float]) -> Tuple[float, int]:
    """Cochran's Q under fixed-effect weights."""
    if any(vi <= 0 for vi in v):
        raise ValueError("All variances must be > 0")
    w = [1.0 / vi for vi in v]
    mu = _wmean(y, w)
    Q = sum(wi * (yi - mu) ** 2 for yi, wi in zip(y, w))
    df = len(y) - 1
    return Q, df


def dersimonian_laird_tau2(y: Sequence[float], v: Sequence[float]) -> float:
    """DerSimonian-Laird estimator for between-study variance tau^2."""
    Q, df = heterogeneity_Q(y, v)
    w = [1.0 / vi for vi in v]
    sw = sum(w)
    sw2 = sum(wi * wi for wi in w)
    C = sw - (sw2 / sw if sw > 0 else 0.0)
    if C <= 0:
        return 0.0
    return max(0.0, (Q - df) / C)


def random_effects(y: Iterable[float], v: Iterable[float], tau2: Optional[float] = None) -> MetaResult:
    """Inverse-variance random-effects pooling (DerSimonian-Laird by default)."""
    yy = _to_list_floats(y)
    vv = _to_list_floats(v)
    _check_lengths(yy, vv)
    if any(vi <= 0 for vi in vv):
        raise ValueError("All variances must be > 0")
    Q, df = heterogeneity_Q(yy, vv)
    t2 = dersimonian_laird_tau2(yy, vv) if tau2 is None else float(tau2)
    w = [1.0 / (vi + t2) for vi in vv]
    est = _wmean(yy, w)
    se = _pooled_se(w)
    lo, hi = ci_normal(est, se)
    I2 = (max(0.0, (Q - df) / Q) * 100.0) if Q > 0 else 0.0
    return MetaResult(model="random", k=len(yy), est=est, se=se, ci_low=lo, ci_high=hi, Q=Q, df=df, tau2=t2, I2=I2)


def summary_table(y: Iterable[float], se: Iterable[float]) -> List[Dict[str, float]]:
    """Convenience helper: accept effects and standard errors, return summary rows."""
    yy = _to_list_floats(y)
    ss = _to_list_floats(se)
    _check_lengths(yy, ss)
    vv = [s * s for s in ss]
    fe = fixed_effect(yy, vv)
    re = random_effects(yy, vv)
    return [fe.as_row(), re.as_row()]


def toy_data() -> Dict[str, List[float]]:
    """Small toy dataset (effects + SEs) used by runnable analysis skeleton."""
    y = [0.20, 0.10, 0.35, 0.05, 0.40]
    se = [0.10, 0.12, 0.15, 0.11, 0.20]
    return {"effect": y, "se": se}
