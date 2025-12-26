"""Prototype numerical experiments (NumPy-based).

The goal is to provide small, dependency-light simulations/sweeps that can be
called from notebooks or CLI wrappers to illustrate qualitative behaviors:
- bifurcation/chaos via the logistic map
- stability checks of linear dynamical systems via eigenvalues
- simple ODE simulation via fixed-step RK4
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Optional, Tuple

import numpy as np
Array = np.ndarray


@dataclass(frozen=True)
class RK4Result:
    t: Array
    y: Array  # shape (len(t), dim)


def rk4_integrate(
    f: Callable[[float, Array], Array],
    y0: Array,
    t: Array,
) -> RK4Result:
    """Fixed-step RK4 integrator with user-provided time grid."""
    t = np.asarray(t, dtype=float)
    y0 = np.asarray(y0, dtype=float)
    y = np.empty((t.size, y0.size), dtype=float)
    y[0] = y0
    for i in range(t.size - 1):
        h = t[i + 1] - t[i]
        ti, yi = t[i], y[i]
        k1 = f(ti, yi)
        k2 = f(ti + 0.5 * h, yi + 0.5 * h * k1)
        k3 = f(ti + 0.5 * h, yi + 0.5 * h * k2)
        k4 = f(ti + h, yi + h * k3)
        y[i + 1] = yi + (h / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
    return RK4Result(t=t, y=y)
def logistic_map(r: float, x0: float, n: int) -> Array:
    """Iterate x_{k+1} = r x_k (1 - x_k) for n steps (returns length n+1)."""
    x = np.empty(n + 1, dtype=float)
    x[0] = float(x0)
    for k in range(n):
        x[k + 1] = r * x[k] * (1.0 - x[k])
    return x


def logistic_bifurcation_sweep(
    r: Array,
    x0: float = 0.2,
    n_transient: int = 500,
    n_samples: int = 200,
) -> Dict[str, Array]:
    """Return samples after transients for each r (for bifurcation diagrams).

    Output:
      r: (m,) values
      x: (m, n_samples) samples from the tail trajectory
    """
    r = np.asarray(r, dtype=float)
    m = r.size
    x_tail = np.empty((m, n_samples), dtype=float)
    for i, ri in enumerate(r):
        traj = logistic_map(float(ri), x0, n_transient + n_samples)
        x_tail[i] = traj[-n_samples:]
    return {"r": r, "x": x_tail}
def linear_stability(A: Array, discrete: bool = False) -> Dict[str, object]:
    """Stability check via eigenvalues.

    continuous-time: x' = A x is asymptotically stable iff Re(lambda)<0 for all.
    discrete-time:   x_{k+1} = A x_k stable iff |lambda|<1 for all.
    """
    A = np.asarray(A, dtype=float)
    eig = np.linalg.eigvals(A)
    if discrete:
        metric = np.abs(eig)
        stable = bool(np.all(metric < 1.0))
        margin = float(1.0 - metric.max())
    else:
        metric = np.real(eig)
        stable = bool(np.all(metric < 0.0))
        margin = float(-metric.max())
    return {"eigs": eig, "stable": stable, "margin": margin, "discrete": discrete}
def van_der_pol(mu: float) -> Callable[[float, Array], Array]:
    """Van der Pol oscillator as a closure suitable for rk4_integrate."""
    mu = float(mu)

    def f(_t: float, y: Array) -> Array:
        x, v = y
        return np.array([v, mu * (1.0 - x * x) * v - x], dtype=float)

    return f


def vdp_limit_cycle_experiment(
    mu: float = 3.0,
    t_span: Tuple[float, float] = (0.0, 40.0),
    dt: float = 0.01,
    y0: Tuple[float, float] = (2.0, 0.0),
) -> Dict[str, Array]:
    """Integrate van der Pol and return a downsampled trajectory."""
    t0, t1 = map(float, t_span)
    n = int(np.floor((t1 - t0) / dt)) + 1
    t = t0 + dt * np.arange(n, dtype=float)
    res = rk4_integrate(van_der_pol(mu), np.array(y0, dtype=float), t)
    return {"t": res.t, "y": res.y, "mu": np.array([mu], dtype=float)}
def run_smoke() -> Dict[str, object]:
    """Small, fast run returning summary scalars for Definition-of-Done checks."""
    sweep = logistic_bifurcation_sweep(np.linspace(2.5, 4.0, 25), n_transient=200, n_samples=50)
    stab = linear_stability(np.array([[-1.0, 2.0], [-3.0, -4.0]]))
    vdp = vdp_limit_cycle_experiment(mu=2.0, t_span=(0.0, 10.0), dt=0.02)
    return {
        "logistic": {"r_min": float(sweep["r"].min()), "r_max": float(sweep["r"].max()), "x_std": float(sweep["x"].std())},
        "linear": {"stable": bool(stab["stable"]), "margin": float(stab["margin"])},
        "vdp": {"t_final": float(vdp["t"][-1]), "y_norm_final": float(np.linalg.norm(vdp["y"][-1]))},
    }


__all__ = [
    "RK4Result",
    "rk4_integrate",
    "logistic_map",
    "logistic_bifurcation_sweep",
    "linear_stability",
    "van_der_pol",
    "vdp_limit_cycle_experiment",
    "run_smoke",
]
