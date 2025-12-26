"""Symbolic + numerical RG flow toy model (phi^4 in 4-eps).

Implements the one-loop beta function
    dλ/dt = -ε λ + a λ^2,   a = 3/(16π^2)
with t = log(μ/μ0). Produces reproducible plots and a small JSON summary.

Run:
    python -m experiments.symbolic_rg_flow --outdir outputs/rg
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import json
import math

import numpy as np
import sympy as sp
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt
A_DEFAULT = 3.0 / (16.0 * math.pi**2)


@dataclass(frozen=True)
class RGModel:
    eps: float = 0.1
    a: float = A_DEFAULT

    def beta(self, lam: float) -> float:
        return -self.eps * lam + self.a * lam * lam

    def fixed_points(self) -> tuple[float, float]:
        return (0.0, 0.0 if self.a == 0 else self.eps / self.a)
def symbolic_derivation(eps: float, a: float) -> dict[str, str]:
    """Return SymPy expressions (as strings) for beta, fixed points, and λ(t)."""
    t = sp.Symbol("t", real=True)
    lam = sp.Function("lam")
    eps_s = sp.Symbol("eps", real=True)
    a_s = sp.Symbol("a", real=True)

    ode = sp.Eq(sp.Derivative(lam(t), t), -eps_s * lam(t) + a_s * lam(t) ** 2)
    sol = sp.dsolve(ode)
    rhs = sp.simplify(sol.rhs)

    # Express in terms of an initial condition lam0 at t=0
    lam0 = sp.Symbol("lam0", real=True)
    C1 = sp.Symbol("C1")
    rhs_ic = sp.simplify(rhs.subs(C1, 1 / lam0 - a_s / eps_s))
    rhs_ic = sp.simplify(rhs_ic.subs({eps_s: eps, a_s: a}))

    beta = sp.simplify(-eps_s * sp.Symbol("λ") + a_s * sp.Symbol("λ") ** 2)
    fp = sp.solve(sp.Eq(beta, 0), sp.Symbol("λ"))

    return {
        "ode": str(ode),
        "solution_general": str(rhs),
        "solution_ic": str(rhs_ic),
        "beta": str(beta),
        "fixed_points": str(fp),
        "latex_solution_ic": sp.latex(rhs_ic),
    }
def analytic_lambda(t: np.ndarray, lam0: float, eps: float, a: float) -> np.ndarray:
    """Closed-form solution for dλ/dt = -ε λ + a λ^2 with λ(0)=λ0."""
    t = np.asarray(t, dtype=float)
    if abs(eps) < 1e-14:
        # dλ/dt = a λ^2 => 1/λ(t) = 1/λ0 - a t
        return 1.0 / (1.0 / lam0 - a * t)
    expm = np.exp(-eps * t)
    denom = (1.0 / lam0 - a / eps) * expm + a / eps
    return 1.0 / denom


def integrate_numeric(model: RGModel, lam0: float, t_span: tuple[float, float], n: int = 400):
    t_eval = np.linspace(t_span[0], t_span[1], n)
    sol = solve_ivp(lambda tt, y: model.beta(float(y[0])), t_span, [lam0], t_eval=t_eval, rtol=1e-9, atol=1e-12)
    return sol.t, sol.y[0]
def plot_flows(outdir: Path, model: RGModel, lam0_list: list[float], tmax: float) -> dict:
    outdir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({
        "figure.dpi": 130,
        "savefig.dpi": 130,
        "axes.grid": True,
        "font.size": 10,
    })

    t_span = (0.0, float(tmax))
    t = np.linspace(*t_span, 600)

    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    for lam0 in lam0_list:
        lam_a = analytic_lambda(t, lam0, model.eps, model.a)
        tn, lam_n = integrate_numeric(model, lam0, t_span)
        ax.plot(t, lam_a, lw=2, label=f"analytic λ0={lam0:g}")
        ax.plot(tn, lam_n, lw=1, ls="--", color=ax.lines[-1].get_color(), label=f"numeric  λ0={lam0:g}")

    fp0, fp1 = model.fixed_points()
    ax.axhline(fp0, color="k", lw=1, alpha=0.5)
    if fp1 != fp0:
        ax.axhline(fp1, color="k", lw=1, alpha=0.5)
        ax.text(0.02 * tmax, fp1, f"  λ*={fp1:.4g}", va="bottom")

    ax.set_xlabel("t = log(μ/μ0)")
    ax.set_ylabel("λ(t)")
    ax.set_title(f"RG flow: dλ/dt = -ε λ + a λ² (ε={model.eps:g}, a={model.a:.4g})")
    ax.set_ylim(bottom=min(-0.5, np.nanmin([ax.get_ylim()[0]])))
    ax.legend(ncol=2, fontsize=8, frameon=True)

    png = outdir / "rg_flow.png"
    fig.tight_layout()
    fig.savefig(png)
    plt.close(fig)

    return {"plot": str(png), "fixed_points": [fp0, fp1]}
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eps", type=float, default=0.1, help="epsilon in 4-eps (default: 0.1)")
    ap.add_argument("--a", type=float, default=A_DEFAULT, help="one-loop coefficient a (default: 3/(16π²))")
    ap.add_argument("--tmax", type=float, default=8.0, help="max RG time (default: 8)")
    ap.add_argument("--lam0", type=float, nargs="*", default=[0.05, 0.2, 0.6], help="initial λ values")
    ap.add_argument("--outdir", type=Path, default=Path("outputs/rg_flow"), help="output directory")
    args = ap.parse_args(argv)

    model = RGModel(eps=args.eps, a=args.a)
    sym = symbolic_derivation(args.eps, args.a)
    res = plot_flows(args.outdir, model, list(args.lam0), args.tmax)

    payload = {
        "model": {"eps": model.eps, "a": model.a},
        "symbolic": sym,
        "results": res,
        "lam0": list(args.lam0),
        "tmax": args.tmax,
    }
    jpath = args.outdir / "rg_flow_summary.json"
    jpath.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    print(f"WROTE {res['plot']}")
    print(f"WROTE {jpath}")
    print("LATEX λ(t) =", sym["latex_solution_ic"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
