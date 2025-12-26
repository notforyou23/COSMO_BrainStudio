"""Scaling-analysis utilities for spin-foam/GFT continuum-recovery diagnostics.

Core features:
- effective (local) scaling exponents from log-derivatives
- finite-size scaling (FSS) rescaling + collapse scoring
- hyperscaling consistency checks for exponent sets
- bootstrap resampling and simple error propagation
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Mapping, Optional, Sequence, Tuple

import numpy as np
def _as_1d(a) -> np.ndarray:
    a = np.asarray(a)
    return a.ravel() if a.ndim else a.reshape(1)


def effective_exponent(x, y, *, loglog: bool = True) -> Tuple[np.ndarray, np.ndarray]:
    """Return (x_mid, alpha_eff) from finite-difference log-derivatives.

    If loglog=True: alpha_eff = d log(y) / d log(x); else d y / d x.
    Assumes x is strictly monotone.
    """
    x = _as_1d(x).astype(float)
    y = _as_1d(y).astype(float)
    if x.size != y.size or x.size < 3:
        raise ValueError("x and y must have same length >= 3")
    if not (np.all(np.diff(x) > 0) or np.all(np.diff(x) < 0)):
        raise ValueError("x must be strictly monotone")
    if loglog:
        if np.any(x <= 0) or np.any(y <= 0):
            raise ValueError("loglog requires x>0 and y>0")
        lx, ly = np.log(x), np.log(y)
        slope = np.diff(ly) / np.diff(lx)
    else:
        slope = np.diff(y) / np.diff(x)
    xmid = 0.5 * (x[1:] + x[:-1])
    return xmid, slope
def moving_window_exponent(x, y, *, k: int = 5) -> Tuple[np.ndarray, np.ndarray]:
    """Least-squares local exponent over a moving window in log-log space.

    Fits log(y)=a*log(x)+b on windows of size k; returns window centers.
    """
    x = _as_1d(x).astype(float)
    y = _as_1d(y).astype(float)
    if k < 3 or k > x.size:
        raise ValueError("k must satisfy 3 <= k <= len(x)")
    if np.any(x <= 0) or np.any(y <= 0):
        raise ValueError("requires x>0 and y>0")
    lx, ly = np.log(x), np.log(y)
    alphas, xc = [], []
    for i in range(x.size - k + 1):
        X = lx[i : i + k]
        Y = ly[i : i + k]
        A = np.vstack([X, np.ones_like(X)]).T
        a, _b = np.linalg.lstsq(A, Y, rcond=None)[0]
        alphas.append(a)
        xc.append(np.exp(np.mean(X)))
    return np.asarray(xc), np.asarray(alphas)
@dataclass(frozen=True)
class FSSRescale:
    """Finite-size scaling rescaling map.

    Typical use: t = (g-gc)/gc and observable O(g,L) ~ L^{-yO} f(t L^{1/nu}).
    Provide yO = beta/nu (magnetization), -gamma/nu (susceptibility), etc.
    """
    nu: float
    yO: float
    gc: float

    def transform(self, g, O, L) -> Tuple[np.ndarray, np.ndarray]:
        g = np.asarray(g, float)
        O = np.asarray(O, float)
        L = np.asarray(L, float)
        t = (g - self.gc) / self.gc
        x = t * (L ** (1.0 / self.nu))
        y = O * (L ** (self.yO))
        return x, y
def collapse_score(
    curves: Sequence[Tuple[np.ndarray, np.ndarray]],
    *,
    nbins: int = 30,
    xlim: Optional[Tuple[float, float]] = None,
) -> float:
    """Quantify curve collapse (lower is better) using binned variance.

    curves: list of (x_rescaled, y_rescaled). Uses common x-range overlap.
    Returns mean over bins of Var(y)/Mean(y)^2 (scale-invariant).
    """
    if len(curves) < 2:
        raise ValueError("need at least two curves")
    xs = [np.asarray(c[0], float) for c in curves]
    ys = [np.asarray(c[1], float) for c in curves]
    xmin = max(np.min(x) for x in xs)
    xmax = min(np.max(x) for x in xs)
    if xlim is not None:
        xmin, xmax = max(xmin, xlim[0]), min(xmax, xlim[1])
    if not np.isfinite([xmin, xmax]).all() or xmax <= xmin:
        return np.inf
    edges = np.linspace(xmin, xmax, nbins + 1)
    scores = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        vals = []
        for x, y in zip(xs, ys):
            m = (x >= lo) & (x < hi)
            if np.any(m):
                vals.append(np.nanmean(y[m]))
        if len(vals) >= 2:
            v = np.nanvar(vals)
            mu = np.nanmean(vals)
            if np.isfinite(v) and np.isfinite(mu) and mu != 0:
                scores.append(v / (mu * mu))
    return float(np.nanmean(scores)) if scores else np.inf
def grid_search_collapse(
    g_list: Sequence[np.ndarray],
    O_list: Sequence[np.ndarray],
    L_list: Sequence[float],
    *,
    nus: Sequence[float],
    yOs: Sequence[float],
    gcs: Sequence[float],
    nbins: int = 30,
) -> Dict[str, float]:
    """Brute-force search for best FSS collapse parameters.

    Inputs are per-size arrays: g_list[i], O_list[i] for system size L_list[i].
    Returns dict with best nu, yO, gc, score.
    """
    if not (len(g_list) == len(O_list) == len(L_list) >= 2):
        raise ValueError("g_list, O_list, L_list must have same length >= 2")
    best = {"nu": np.nan, "yO": np.nan, "gc": np.nan, "score": np.inf}
    for nu in nus:
        for yO in yOs:
            for gc in gcs:
                tr = FSSRescale(nu=float(nu), yO=float(yO), gc=float(gc))
                curves = [tr.transform(g, O, L) for g, O, L in zip(g_list, O_list, L_list)]
                sc = collapse_score(curves, nbins=nbins)
                if sc < best["score"]:
                    best = {"nu": float(nu), "yO": float(yO), "gc": float(gc), "score": float(sc)}
    return best
def hyperscaling_residuals(exponents: Mapping[str, float], *, d: Optional[float] = None) -> Dict[str, float]:
    """Return residuals of common hyperscaling/scaling relations.

    Supports keys among: alpha,beta,gamma,delta,nu,eta; optional dimension d.
    Residuals are LHS-RHS for each relation that can be evaluated.
    """
    e = {k: float(v) for k, v in exponents.items()}
    r: Dict[str, float] = {}
    if {"alpha", "beta", "gamma"} <= e.keys():
        r["rushbrooke: alpha+2beta+gamma=2"] = e["alpha"] + 2 * e["beta"] + e["gamma"] - 2
    if {"gamma", "beta", "delta"} <= e.keys():
        r["widom: gamma=beta(delta-1)"] = e["gamma"] - e["beta"] * (e["delta"] - 1)
    if {"gamma", "nu", "eta"} <= e.keys():
        r["fisher: gamma=(2-eta)nu"] = e["gamma"] - (2 - e["eta"]) * e["nu"]
    if d is not None and {"alpha", "nu"} <= e.keys():
        r["josephson: 2-alpha=d nu"] = (2 - e["alpha"]) - float(d) * e["nu"]
    return r
def propagate_uncertainty(
    f: Callable[[np.ndarray], float],
    x: Sequence[float],
    cov: np.ndarray,
    *,
    eps: float = 1e-6,
) -> float:
    """Delta-method std for f(x) given covariance of x (numerical Jacobian)."""
    x = np.asarray(x, float)
    cov = np.asarray(cov, float)
    if cov.shape != (x.size, x.size):
        raise ValueError("cov must be square (n,n) matching x")
    fx = float(f(x))
    J = np.zeros_like(x)
    for i in range(x.size):
        dx = np.zeros_like(x)
        dx[i] = eps * (1.0 + abs(x[i]))
        J[i] = (float(f(x + dx)) - fx) / dx[i]
    var = float(J @ cov @ J)
    return float(np.sqrt(max(var, 0.0)))


def bootstrap(
    data: np.ndarray,
    stat: Callable[[np.ndarray], np.ndarray],
    *,
    n: int = 500,
    rng: Optional[np.random.Generator] = None,
    ci: float = 0.68,
) -> Dict[str, np.ndarray]:
    """Bootstrap a statistic over first axis; returns mean/std and central CI."""
    rng = np.random.default_rng() if rng is None else rng
    x = np.asarray(data)
    if x.ndim == 0:
        raise ValueError("data must be array-like")
    m = x.shape[0]
    reps = []
    for _ in range(int(n)):
        idx = rng.integers(0, m, size=m)
        reps.append(np.asarray(stat(x[idx])))
    reps = np.stack(reps, axis=0)
    mean = np.nanmean(reps, axis=0)
    std = np.nanstd(reps, axis=0, ddof=1)
    lo = np.nanquantile(reps, (1 - ci) / 2, axis=0)
    hi = np.nanquantile(reps, 1 - (1 - ci) / 2, axis=0)
    return {"mean": mean, "std": std, "ci_lo": lo, "ci_hi": hi}
