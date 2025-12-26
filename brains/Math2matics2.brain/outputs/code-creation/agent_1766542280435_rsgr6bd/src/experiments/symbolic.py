"""Symbolic derivations for three small reference experiments.

This module provides stepwise SymPy transformations that yield simplified
closed-form expressions suitable for lambdified numeric evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

import sympy as sp


@dataclass(frozen=True)
class Derivation:
    """A lightweight container capturing symbolic steps and final form."""

    steps: tuple[tuple[str, sp.Expr], ...]
    final: sp.Expr

    def simplify(self) -> "Derivation":
        simp_steps = tuple((d, sp.simplify(e)) for d, e in self.steps)
        return Derivation(simp_steps, sp.simplify(self.final))


def _as_derivation(steps: Iterable[tuple[str, sp.Expr]], final: sp.Expr) -> Derivation:
    return Derivation(tuple(steps), final)


def lambdify_expr(expr: sp.Expr, args: Iterable[sp.Symbol]) -> Callable:
    """Return a NumPy-ready callable for *expr*.

    Numeric code uses this to evaluate symbolic closed forms.
    """

    return sp.lambdify(tuple(args), expr, modules=["numpy"])
# ---- Experiment 1: finite geometric series (and stable ratio form) ----


def exp1_geometric_series() -> Derivation:
    """Derive S = sum_{k=0}^{n-1} r**k as a closed form."""

    r, n = sp.symbols("r n")
    k = sp.Symbol("k", integer=True)
    S = sp.summation(r**k, (k, 0, n - 1))
    steps = [("definition", S)]
    closed = sp.simplify(S)
    steps.append(("sympy_summation", closed))
    # alternative stable form: expm1/log1p analog in ratio space
    stable = sp.simplify((1 - r**n) / (1 - r))
    steps.append(("ratio_form", stable))
    return _as_derivation(steps, stable)


def exp1_closed_form_symbols():
    r, n = sp.symbols("r n")
    return r, n, exp1_geometric_series().final
# ---- Experiment 2: affine scalar ODE x' = a x + b ----


def exp2_affine_ode_solution() -> Derivation:
    """Solve x'(t) = a*x(t) + b with x(0)=x0 and simplify."""

    t = sp.symbols("t", real=True)
    a, b, x0 = sp.symbols("a b x0")
    x = sp.Function("x")
    ode = sp.Eq(sp.diff(x(t), t), a * x(t) + b)
    steps = [("ode", ode)]
    sol = sp.dsolve(ode, ics={x(0): x0})
    steps.append(("dsolve", sol.rhs))
    rhs = sp.simplify(sol.rhs)
    steps.append(("simplify", rhs))
    # also provide the a->0 continuous limit (for numeric stability checks)
    limit_a0 = sp.simplify(sp.limit(rhs, a, 0))
    steps.append(("limit_a_to_0", limit_a0))
    return _as_derivation(steps, rhs)


def exp2_closed_form_symbols():
    t = sp.symbols("t", real=True)
    a, b, x0 = sp.symbols("a b x0")
    return t, a, b, x0, exp2_affine_ode_solution().final
# ---- Experiment 3: Normal-Normal conjugate posterior mean/variance ----


def exp3_normal_normal_posterior() -> Derivation:
    """Derive posterior for Normal prior + Normal likelihood (known variance).

    Prior:   mu ~ Normal(mu0, s0^2)
    Data:    xi ~ Normal(mu, s^2), i=1..n
    Returns posterior mean m_n and variance s_n^2.
    """

    mu0, s0, s = sp.symbols("mu0 s0 s", positive=True)
    n = sp.Symbol("n", integer=True, positive=True)
    xbar = sp.symbols("xbar", real=True)  # sufficient statistic
    prec0 = 1 / s0**2
    prec = n / s**2
    steps = [("prior_precision", prec0), ("lik_precision", prec)]
    post_var = 1 / (prec0 + prec)
    steps.append(("posterior_variance", post_var))
    post_mean = sp.simplify(post_var * (prec0 * mu0 + prec * xbar))
    steps.append(("posterior_mean", post_mean))
    # common weighted-average form
    w = sp.simplify(prec / (prec0 + prec))
    mean_wa = sp.simplify((1 - w) * mu0 + w * xbar)
    steps.append(("weighted_average_form", mean_wa))
    final = sp.Matrix([mean_wa, sp.simplify(post_var)])
    return _as_derivation(steps, final)


def exp3_closed_form_symbols():
    mu0, s0, s = sp.symbols("mu0 s0 s", positive=True)
    n = sp.Symbol("n", integer=True, positive=True)
    xbar = sp.symbols("xbar", real=True)
    expr = exp3_normal_normal_posterior().final
    return mu0, s0, s, n, xbar, expr
