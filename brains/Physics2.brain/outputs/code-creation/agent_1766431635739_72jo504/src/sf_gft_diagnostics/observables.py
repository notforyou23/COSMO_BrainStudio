"""Continuum-recovery observables for spin-foam / GFT renormalization.

This module provides a *prioritized* catalog of candidate continuum observables and
scaling quantities, with lightweight schemas and computable estimators.

Conventions:
- Estimators consume an in-memory mapping ``data: dict`` (produced by rg_io adapters).
- Missing required keys raise ``KeyError`` with a clear message.
- Returned values are numpy scalars/arrays, suitable for bootstraps/FSS in scaling.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

import numpy as np
Array = np.ndarray
Data = Mapping[str, Any]
Estimator = Callable[[Data], Any]


@dataclass(frozen=True)
class ObservableSpec:
    """Specification for a computable diagnostic observable."""

    name: str
    priority: int  # 1 = highest
    description: str
    requires: Tuple[str, ...]
    schema: Dict[str, Any]
    estimator: Estimator

    def compute(self, data: Data) -> Any:
        for k in self.requires:
            if k not in data:
                raise KeyError(f"Observable '{self.name}' requires key '{k}'")
        return self.estimator(data)
def _as_array(x: Any) -> Array:
    return np.asarray(x)


def _mean_var(x: Any) -> Tuple[float, float]:
    a = _as_array(x).astype(float)
    return float(np.mean(a)), float(np.var(a, ddof=1) if a.size > 1 else 0.0)


def _safe_log(x: Array, eps: float = 1e-300) -> Array:
    return np.log(np.maximum(_as_array(x).astype(float), eps))
# ---- Estimators (generic, dataset-key based) ---------------------------------


def est_mean_volume(data: Data) -> float:
    """Mean 4-volume proxy (e.g. number of 4-simplices, or GFT quanta)."""
    m, _ = _mean_var(data["volume"])
    return m


def est_volume_susceptibility(data: Data) -> float:
    """Var(V)/<V> as a coarse analog of compressibility/susceptibility."""
    m, v = _mean_var(data["volume"])
    return float(v / (m + 1e-30))


def est_binder_volume(data: Data) -> float:
    """Binder cumulant of volume: 1 - <V^4>/(3 <V^2>^2)."""
    V = _as_array(data["volume"]).astype(float)
    v2 = np.mean(V**2)
    v4 = np.mean(V**4)
    return float(1.0 - v4 / (3.0 * (v2**2 + 1e-30)))


def est_spin_mean(data: Data) -> float:
    """Mean spin from a histogram or sample list (proxy for area scale)."""
    j = _as_array(data["spin"]).astype(float)
    return float(np.mean(j))


def est_spin_entropy(data: Data) -> float:
    """Shannon entropy of spin distribution (requires prob vector 'spin_p')."""
    p = _as_array(data["spin_p"]).astype(float)
    p = p / (np.sum(p) + 1e-30)
    return float(-np.sum(p * _safe_log(p)))


def est_two_point_connected(data: Data) -> Array:
    """Connected correlator C(r)=<O_x O_{x+r}>-<O>^2 provided as raw arrays."""
    oo = _as_array(data["two_point"]).astype(float)  # shape (R,) or (nsamp,R)
    o = _as_array(data["one_point"]).astype(float)   # scalar or (nsamp,)
    return np.mean(oo, axis=0) - (np.mean(o) ** 2)


def est_corr_length_second_moment(data: Data) -> float:
    """Second-moment correlation length from C(r) and radii r."""
    r = _as_array(data["r"]).astype(float)
    C = _as_array(data["C_r"]).astype(float)
    C0 = np.sum(C)
    if C0 <= 0:
        return float(np.nan)
    xi2 = np.sum((r**2) * C) / (2.0 * C0 + 1e-30)
    return float(np.sqrt(max(xi2, 0.0)))


def est_spectral_dimension(data: Data) -> float:
    """Spectral dimension from return prob P(s): d_s=-2 d ln P / d ln s."""
    s = _as_array(data["diffusion_time"]).astype(float)
    P = _as_array(data["return_prob"]).astype(float)
    ls, lP = _safe_log(s), _safe_log(P)
    # local slope via least squares on central window if provided
    i0, i1 = data.get("fit_window", (max(1, len(s)//4), max(2, 3*len(s)//4)))
    i0, i1 = int(i0), int(i1)
    A = np.vstack([ls[i0:i1], np.ones(i1 - i0)]).T
    slope, _ = np.linalg.lstsq(A, lP[i0:i1], rcond=None)[0]
    return float(-2.0 * slope)


def est_regge_curvature_rms(data: Data) -> float:
    """RMS deficit angle (proxy for |R| scale) from 'deficit_angles'."""
    d = _as_array(data["deficit_angles"]).astype(float)
    return float(np.sqrt(np.mean(d**2)))
# ---- Prioritized catalog ------------------------------------------------------

CATALOG: List[ObservableSpec] = [
    ObservableSpec(
        name="mean_volume",
        priority=1,
        description="Mean total 4-volume proxy (tracks phase structure and continuum limit at fixed physical volume).",
        requires=("volume",),
        schema={"type": "scalar", "unit": "(l_P)^4 or simplex-count"},
        estimator=est_mean_volume,
    ),
    ObservableSpec(
        name="volume_susceptibility",
        priority=1,
        description="Var(V)/<V> (peaks indicate criticality; useful for FSS).",
        requires=("volume",),
        schema={"type": "scalar", "unit": "dimensionless"},
        estimator=est_volume_susceptibility,
    ),
    ObservableSpec(
        name="binder_volume",
        priority=1,
        description="Binder cumulant for volume (distinguishes 1st vs 2nd order transitions, universality).",
        requires=("volume",),
        schema={"type": "scalar", "range": [-2, 1]},
        estimator=est_binder_volume,
    ),
    ObservableSpec(
        name="spin_mean",
        priority=2,
        description="Mean spin/area scale (monitors coarse-graining drift and 'continuum' scaling of typical quantum numbers).",
        requires=("spin",),
        schema={"type": "scalar", "unit": "dimensionless j"},
        estimator=est_spin_mean,
    ),
    ObservableSpec(
        name="spin_entropy",
        priority=2,
        description="Entropy of spin distribution (checks approach to fixed-point distributions; comparable across RG schemes).",
        requires=("spin_p",),
        schema={"type": "scalar", "unit": "nats"},
        estimator=est_spin_entropy,
    ),
    ObservableSpec(
        name="C_r_connected",
        priority=2,
        description="Connected 2-point correlator (input for correlation length and anomalous scaling).",
        requires=("two_point", "one_point"),
        schema={"type": "array", "axis": "r"},
        estimator=est_two_point_connected,
    ),
    ObservableSpec(
        name="xi_second_moment",
        priority=1,
        description="Second-moment correlation length from C(r) (primary continuum diagnostic; enables FSS collapse).",
        requires=("r", "C_r"),
        schema={"type": "scalar", "unit": "lattice units"},
        estimator=est_corr_length_second_moment,
    ),
    ObservableSpec(
        name="spectral_dimension",
        priority=1,
        description="Spectral dimension from diffusion return probability (robust semiclassical/continuum comparison target).",
        requires=("diffusion_time", "return_prob"),
        schema={"type": "scalar", "unit": "dimensionless", "notes": "fit_window optional"},
        estimator=est_spectral_dimension,
    ),
    ObservableSpec(
        name="regge_curvature_rms",
        priority=3,
        description="RMS deficit angle (curvature proxy; compare with semiclassical/Regge expectations at large scales).",
        requires=("deficit_angles",),
        schema={"type": "scalar", "unit": "radians"},
        estimator=est_regge_curvature_rms,
    ),
]

_BY_NAME: Dict[str, ObservableSpec] = {o.name: o for o in CATALOG}
def list_observables(sort: bool = True) -> List[ObservableSpec]:
    """Return catalog entries (optionally sorted by increasing priority)."""
    obs = list(CATALOG)
    return sorted(obs, key=lambda o: (o.priority, o.name)) if sort else obs


def get_observable(name: str) -> ObservableSpec:
    """Fetch an observable spec by name."""
    try:
        return _BY_NAME[name]
    except KeyError as e:
        raise KeyError(f"Unknown observable '{name}'. Available: {sorted(_BY_NAME)}") from e


def compute(name: str, data: Data) -> Any:
    """Compute an observable by name."""
    return get_observable(name).compute(data)


def compute_many(names: Sequence[str], data: Data) -> Dict[str, Any]:
    """Compute multiple observables, returning a mapping name->value."""
    return {n: compute(n, data) for n in names}
