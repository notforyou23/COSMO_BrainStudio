"""SymPy-based symbolic experiments.

This module provides small, self-contained derivations/checks that can be used
as "analytical consequences" prototypes (gradient/Hessian identities, Jacobians,
etc.) and exports simplified expressions in JSON-friendly form.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Tuple

import sympy as sp
@dataclass(frozen=True)
class PackedExpr:
    """A JSON-friendly bundle of representations for a SymPy expression."""

    srepr: str
    str: str
    latex: str

    @staticmethod
    def of(expr: sp.Expr) -> "PackedExpr":
        e = sp.simplify(expr)
        return PackedExpr(srepr=sp.srepr(e), str=str(e), latex=sp.latex(e))
def check_equivalent(a: sp.Expr, b: sp.Expr) -> bool:
    """Return True if SymPy can simplify (a - b) to 0."""
    return sp.simplify(a - b) == 0
def experiment_quadratic_form(n: int = 2) -> Dict[str, Any]:
    """Verify gradient/Hessian identities for f(x)=x^T A x (explicit small n).

    For general (possibly non-symmetric) A:
      ∇f = (A + Aᵀ) x
      H  = A + Aᵀ
    """
    if n != 2:
        raise ValueError("This prototype uses n=2 to keep expressions compact.")

    x1, x2 = sp.symbols("x1 x2")
    a11, a12, a21, a22 = sp.symbols("a11 a12 a21 a22")
    x = sp.Matrix([x1, x2])
    A = sp.Matrix([[a11, a12], [a21, a22]])

    f = (x.T * A * x)[0]
    grad = sp.Matrix([sp.diff(f, x1), sp.diff(f, x2)])
    H = sp.hessian(f, (x1, x2))
    rhs_grad = (A + A.T) * x
    rhs_H = A + A.T

    return {
        "name": "quadratic_form",
        "inputs": {"n": n},
        "expressions": {
            "f": PackedExpr.of(f).__dict__,
            "grad": PackedExpr.of(grad).__dict__,
            "hessian": PackedExpr.of(H).__dict__,
            "rhs_grad": PackedExpr.of(rhs_grad).__dict__,
            "rhs_hessian": PackedExpr.of(rhs_H).__dict__,
        },
        "checks": {
            "grad_identity": bool(sp.simplify(grad - rhs_grad) == sp.zeros(2, 1)),
            "hessian_identity": bool(sp.simplify(H - rhs_H) == sp.zeros(2)),
        },
    }
def experiment_softmax_jacobian(k: int = 3) -> Dict[str, Any]:
    """Derive Jacobian of softmax and link it to log-sum-exp.

    softmax(z)_i = exp(z_i)/sum_j exp(z_j)
    J = diag(s) - s s^T
    Also: ∇ logsumexp(z) = softmax(z)
    """
    if k != 3:
        raise ValueError("This prototype uses k=3 to keep expressions compact.")

    z1, z2, z3 = sp.symbols("z1 z2 z3")
    z = sp.Matrix([z1, z2, z3])
    exps = sp.Matrix([sp.exp(z1), sp.exp(z2), sp.exp(z3)])
    Z = sp.simplify(sum(exps))
    s = sp.simplify(exps / Z)

    J = s.jacobian((z1, z2, z3))
    J_rhs = sp.diag(*list(s)) - s * s.T

    lse = sp.log(sum(sp.exp(zi) for zi in (z1, z2, z3)))
    grad_lse = sp.Matrix([sp.diff(lse, zi) for zi in (z1, z2, z3)])

    return {
        "name": "softmax_jacobian",
        "inputs": {"k": k},
        "expressions": {
            "softmax": PackedExpr.of(s).__dict__,
            "jacobian": PackedExpr.of(J).__dict__,
            "jacobian_rhs": PackedExpr.of(J_rhs).__dict__,
            "logsumexp": PackedExpr.of(lse).__dict__,
            "grad_logsumexp": PackedExpr.of(grad_lse).__dict__,
        },
        "checks": {
            "jacobian_identity": bool(sp.simplify(J - J_rhs) == sp.zeros(3)),
            "grad_logsumexp_is_softmax": bool(sp.simplify(grad_lse - s) == sp.zeros(3, 1)),
        },
    }
def run_all() -> Dict[str, Any]:
    """Run all symbolic experiments and return a JSON-serializable dict."""
    experiments = [experiment_quadratic_form(), experiment_softmax_jacobian()]
    return {"ok": all(all(e["checks"].values()) for e in experiments), "experiments": experiments}
def main() -> None:
    """CLI entrypoint: print a compact JSON summary to stdout."""
    import json

    print(json.dumps(run_all(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
