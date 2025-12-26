"""sf_gft_diagnostics.metrics

Mutually comparable distance/consistency metrics used to cross-validate RG flows
(tensor-network / lattice RG / spin-foam or GFT coarse-graining logs) and to
benchmark semiclassical/continuum expectations.

Design goals:
- Robust on small sample sizes and sparse histograms (epsilon smoothing).
- Works with minimal dependencies (NumPy only).
- Comparable metrics for (i) distributions, (ii) vectors/observables, (iii) RG trajectories.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Optional, Sequence, Tuple

import numpy as np
Array = np.ndarray


def _as_1d(a: Array) -> Array:
    a = np.asarray(a, dtype=float)
    return a.reshape(-1)


def normalize_pmf(p: Array, eps: float = 1e-12) -> Array:
    """Normalize a nonnegative array to a probability mass function with smoothing."""
    p = np.clip(_as_1d(p), 0.0, np.inf) + float(eps)
    s = p.sum()
    return p / s if s > 0 else np.full_like(p, 1.0 / max(len(p), 1))
def kl_divergence(p: Array, q: Array, eps: float = 1e-12) -> float:
    """KL(p||q) with epsilon-smoothing; returns a finite float."""
    p = normalize_pmf(p, eps)
    q = normalize_pmf(q, eps)
    return float(np.sum(p * (np.log(p) - np.log(q))))


def js_divergence(p: Array, q: Array, eps: float = 1e-12, base: float = 2.0) -> float:
    """Jensen-Shannon divergence (bounded, symmetric)."""
    p = normalize_pmf(p, eps)
    q = normalize_pmf(q, eps)
    m = 0.5 * (p + q)
    js = 0.5 * kl_divergence(p, m, eps) + 0.5 * kl_divergence(q, m, eps)
    return float(js / np.log(base))


def hellinger_distance(p: Array, q: Array, eps: float = 1e-12) -> float:
    p = normalize_pmf(p, eps)
    q = normalize_pmf(q, eps)
    return float(np.linalg.norm(np.sqrt(p) - np.sqrt(q)) / np.sqrt(2.0))
def wasserstein_1d(p: Array, q: Array, x: Optional[Array] = None, eps: float = 1e-12) -> float:
    """1D Wasserstein-1 (Earth mover) for discrete distributions.

    p,q: histogram counts or pmf on a common grid.
    x: locations (same length); defaults to unit spacing.
    """
    p = normalize_pmf(p, eps)
    q = normalize_pmf(q, eps)
    if x is None:
        dx = 1.0
    else:
        x = _as_1d(x)
        if len(x) != len(p):
            raise ValueError("x must have same length as p,q")
        dx = np.diff(x)
        if np.any(dx <= 0):
            raise ValueError("x must be strictly increasing")
        # For nonuniform spacing, integrate CDF difference piecewise.
        cdf = np.cumsum(p - q)[:-1]
        return float(np.sum(np.abs(cdf) * dx))
    cdf = np.cumsum(p - q)
    return float(np.sum(np.abs(cdf)) * dx)
def l1_distance(a: Array, b: Array) -> float:
    a, b = _as_1d(a), _as_1d(b)
    if len(a) != len(b):
        raise ValueError("Inputs must have same length")
    return float(np.sum(np.abs(a - b)))


def l2_distance(a: Array, b: Array) -> float:
    a, b = _as_1d(a), _as_1d(b)
    if len(a) != len(b):
        raise ValueError("Inputs must have same length")
    return float(np.linalg.norm(a - b))


def cosine_distance(a: Array, b: Array, eps: float = 1e-12) -> float:
    a, b = _as_1d(a), _as_1d(b)
    na = np.linalg.norm(a) + eps
    nb = np.linalg.norm(b) + eps
    return float(1.0 - np.dot(a, b) / (na * nb))
def _interp_to_grid(x: Array, y: Array, grid: Array) -> Array:
    x = _as_1d(x)
    y = np.asarray(y, dtype=float)
    if y.ndim == 1:
        y = y[:, None]
    if len(x) != y.shape[0]:
        raise ValueError("x and y must have compatible lengths")
    out = np.vstack([np.interp(grid, x, y[:, j]) for j in range(y.shape[1])]).T
    return out.squeeze()


def curve_rms_distance(
    t1: Array,
    y1: Array,
    t2: Array,
    y2: Array,
    n_grid: int = 128,
    weights: Optional[Array] = None,
) -> float:
    """RMS distance between two parametric curves after interpolation to a common grid."""
    t1, t2 = _as_1d(t1), _as_1d(t2)
    grid = np.linspace(max(t1.min(), t2.min()), min(t1.max(), t2.max()), int(n_grid))
    a = _interp_to_grid(t1, y1, grid)
    b = _interp_to_grid(t2, y2, grid)
    d = a - b
    if d.ndim == 1:
        d = d[:, None]
    if weights is None:
        return float(np.sqrt(np.mean(np.sum(d * d, axis=1))))
    w = normalize_pmf(weights, eps=0.0)
    if len(w) != len(grid):
        raise ValueError("weights must have length n_grid")
    return float(np.sqrt(np.sum(w * np.sum(d * d, axis=1))))
def dtw_distance(seq1: Array, seq2: Array, p: float = 2.0) -> float:
    """Dynamic time warping distance between two sequences (vectors allowed).

    Uses O(nm) DP; intended for short RG trajectories (tens to few hundreds steps).
    """
    x = np.asarray(seq1, dtype=float)
    y = np.asarray(seq2, dtype=float)
    if x.ndim == 1:
        x = x[:, None]
    if y.ndim == 1:
        y = y[:, None]
    n, m = x.shape[0], y.shape[0]
    D = np.full((n + 1, m + 1), np.inf, dtype=float)
    D[0, 0] = 0.0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = np.linalg.norm(x[i - 1] - y[j - 1], ord=p)
            D[i, j] = cost + min(D[i - 1, j], D[i, j - 1], D[i - 1, j - 1])
    return float(D[n, m])
@dataclass(frozen=True)
class Metric:
    name: str
    kind: str  # 'distribution' | 'vector' | 'trajectory'
    fn: Callable[..., float]
    bounded: Optional[Tuple[float, float]] = None
    notes: str = ""


METRICS: Dict[str, Metric] = {
    "kl": Metric("kl", "distribution", kl_divergence, bounded=None, notes="KL(p||q), asymmetric"),
    "js": Metric("js", "distribution", js_divergence, bounded=(0.0, 1.0), notes="JS divergence base-2"),
    "hellinger": Metric("hellinger", "distribution", hellinger_distance, bounded=(0.0, 1.0)),
    "w1": Metric("w1", "distribution", wasserstein_1d, bounded=None, notes="Wasserstein-1 on 1D grid"),
    "l1": Metric("l1", "vector", l1_distance),
    "l2": Metric("l2", "vector", l2_distance),
    "cosine": Metric("cosine", "vector", cosine_distance, bounded=(0.0, 2.0)),
    "curve_rms": Metric("curve_rms", "trajectory", curve_rms_distance),
    "dtw": Metric("dtw", "trajectory", dtw_distance),
}


def get_metric(name: str) -> Metric:
    """Return a metric descriptor by name."""
    if name not in METRICS:
        raise KeyError(f"Unknown metric '{name}'. Available: {sorted(METRICS)}")
    return METRICS[name]
