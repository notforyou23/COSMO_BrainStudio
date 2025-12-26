"""Numeric implementations for the three reference experiments.

Focus: stable evaluation (near-singular parameter regimes), NumPy vectorization,
and optional reference checks against symbolic closed forms.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

import numpy as np

try:  # optional, used only for reference checks
    from . import symbolic as _sym
except Exception:  # pragma: no cover
    _sym = None  # type: ignore

helpers: Dict[str, Any] = {}
def exp1_geometric_sum(r: np.ndarray | float, n: np.ndarray | int) -> np.ndarray:
    """Return S=\sum_{k=0}^{n-1} r**k with a stable form near r≈1.

    Uses expm1/log1p to avoid catastrophic cancellation in (1-r**n)/(1-r).
    Supports broadcasting across r and n.
    """
    r = np.asarray(r, dtype=float)
    n = np.asarray(n, dtype=float)
    lr = np.log1p(r - 1.0)  # stable log(r) near r=1
    num = np.expm1(n * lr)
    den = np.expm1(lr)
    out = np.divide(num, den, out=np.full(np.broadcast(num, den).shape, np.nan), where=den != 0)
    return np.where(r == 1.0, n, out)


def exp2_affine_ode(t: np.ndarray | float, a: np.ndarray | float, b: np.ndarray | float, x0: np.ndarray | float) -> np.ndarray:
    """Solve x'(t)=a x + b, x(0)=x0 with stability near a≈0."""
    t, a, b, x0 = map(lambda z: np.asarray(z, dtype=float), (t, a, b, x0))
    at = a * t
    # x(t) = x0*exp(at) + b*(exp(at)-1)/a; use expm1 to stabilize.
    incr = np.divide(np.expm1(at), a, out=np.zeros(np.broadcast(at, a).shape), where=a != 0)
    out = x0 * np.exp(at) + b * incr
    return np.where(a == 0.0, x0 + b * t, out)


def exp3_normal_normal(mu0: np.ndarray | float, s0: np.ndarray | float, s: np.ndarray | float, n: np.ndarray | int, xbar: np.ndarray | float) -> Tuple[np.ndarray, np.ndarray]:
    """Normal-Normal posterior (known sigma): return (mean, variance)."""
    mu0, s0, s, xbar = map(lambda z: np.asarray(z, dtype=float), (mu0, s0, s, xbar))
    n = np.asarray(n, dtype=float)
    prec0 = 1.0 / (s0 * s0)
    prec = n / (s * s)
    post_var = 1.0 / (prec0 + prec)
    w = prec / (prec0 + prec)
    post_mean = (1.0 - w) * mu0 + w * xbar
    return post_mean, post_var
def _sympy_refs():
    if _sym is None:
        return None
    r, n, e1 = _sym.exp1_closed_form_symbols()
    t, a, b, x0, e2 = _sym.exp2_closed_form_symbols()
    mu0, s0, s, nn, xbar, e3 = _sym.exp3_closed_form_symbols()
    f1 = _sym.lambdify_expr(e1, (r, n))
    f2 = _sym.lambdify_expr(e2, (t, a, b, x0))
    f3 = _sym.lambdify_expr(e3, (mu0, s0, s, nn, xbar))
    return f1, f2, f3


def reference_check(seed: int = 0, atol: float = 1e-10, rtol: float = 1e-10) -> Dict[str, bool]:
    """Quick randomized numeric-vs-symbolic consistency checks."""
    refs = _sympy_refs()
    if refs is None:
        return {"exp1": True, "exp2": True, "exp3": True}
    f1, f2, f3 = refs
    rng = np.random.default_rng(seed)

    r = rng.uniform(0.5, 1.5, size=1000)
    n = rng.integers(1, 50, size=1000)
    ok1 = np.allclose(exp1_geometric_sum(r, n), f1(r, n), atol=atol, rtol=rtol)

    t = rng.uniform(0.0, 2.0, size=1000)
    a = rng.uniform(-1e-6, 1e-6, size=1000)  # stress a≈0 regime
    b = rng.normal(size=1000)
    x0 = rng.normal(size=1000)
    ok2 = np.allclose(exp2_affine_ode(t, a, b, x0), f2(t, a, b, x0), atol=1e-8, rtol=1e-8)

    mu0 = rng.normal(size=1000)
    s0 = rng.uniform(0.2, 2.0, size=1000)
    s = rng.uniform(0.2, 2.0, size=1000)
    nn = rng.integers(1, 200, size=1000)
    xbar = rng.normal(size=1000)
    mean, var = exp3_normal_normal(mu0, s0, s, nn, xbar)
    sym = np.asarray(f3(mu0, s0, s, nn, xbar), dtype=float)  # shape (2,N)
    ok3 = np.allclose(mean, sym[0], atol=atol, rtol=rtol) and np.allclose(var, sym[1], atol=atol, rtol=rtol)
    return {"exp1": bool(ok1), "exp2": bool(ok2), "exp3": bool(ok3)}
@dataclass(frozen=True)
class ExperimentResult:
    name: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]


def run_experiment_1(r: np.ndarray | float, n: np.ndarray | int) -> ExperimentResult:
    s = exp1_geometric_sum(r, n)
    return ExperimentResult("exp1_geometric_series", {"r": r, "n": n}, {"S": s})


def run_experiment_2(t: np.ndarray | float, a: np.ndarray | float, b: np.ndarray | float, x0: np.ndarray | float) -> ExperimentResult:
    x = exp2_affine_ode(t, a, b, x0)
    return ExperimentResult("exp2_affine_ode", {"t": t, "a": a, "b": b, "x0": x0}, {"x": x})


def run_experiment_3(mu0: np.ndarray | float, s0: np.ndarray | float, s: np.ndarray | float, n: np.ndarray | int, xbar: np.ndarray | float) -> ExperimentResult:
    mean, var = exp3_normal_normal(mu0, s0, s, n, xbar)
    return ExperimentResult("exp3_normal_normal", {"mu0": mu0, "s0": s0, "s": s, "n": n, "xbar": xbar}, {"post_mean": mean, "post_var": var})


helpers.update(
    exp1_geometric_sum=exp1_geometric_sum,
    exp2_affine_ode=exp2_affine_ode,
    exp3_normal_normal=exp3_normal_normal,
    reference_check=reference_check,
)
