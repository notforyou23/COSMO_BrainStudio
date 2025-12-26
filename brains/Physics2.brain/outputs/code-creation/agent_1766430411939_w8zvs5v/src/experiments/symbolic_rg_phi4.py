#!/usr/bin/env python3
\"\"\"Symbolic + toy numerical RG flow for a φ^4-like theory.

We use a standard one-loop Wilson-Fisher-style beta function model in d=4-ε:
  β_λ = dλ/dt = -ε λ + 3 λ^2/(16π^2)
  β_m2 = dm^2/dt = (-2 + λ/(16π^2)) m^2
where t = log(μ/μ0) is RG "time" and m^2, λ are dimensionless couplings.

The script prints LaTeX for the beta functions and fixed points, and saves
a small phase-portrait plot (λ vs m^2) for a few initial conditions.
\"\"\"

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import sympy as sp
import matplotlib.pyplot as plt
def symbolic_report(eps: float) -> str:
    lam, m2, pi, eps_s = sp.symbols("lambda m^2 pi epsilon", positive=True, real=True)
    beta_lam = -eps_s * lam + sp.Rational(3, 1) * lam**2 / (16 * pi**2)
    beta_m2 = (-2 + lam / (16 * pi**2)) * m2

    # Fixed points: solve β_λ=0 for λ; m^2 is a relevant perturbation at WF.
    fp_lam = sp.solve(sp.Eq(beta_lam, 0), lam)
    wf = sp.simplify(fp_lam[1])  # 16 π^2 ε / 3
    # Linearized eigenvalues at fixed points (λ, m^2) for (β_λ, β_m2)
    J = sp.Matrix([beta_lam, beta_m2]).jacobian([lam, m2])
    evals_g = [sp.simplify(ev) for ev in J.subs({lam: 0, m2: 0}).eigenvals().keys()]
    evals_wf = [sp.simplify(ev) for ev in J.subs({lam: wf, m2: 0}).eigenvals().keys()]

    subs_num = {eps_s: sp.nsimplify(eps)}
    lines = []
    lines.append("=== Toy φ^4 RG (one-loop, d=4-ε) ===")
    lines.append(f"epsilon = {eps:g}")
    lines.append("")
    lines.append("Beta functions (symbolic):")
    lines.append("  β_λ = " + sp.latex(beta_lam))
    lines.append("  β_{m^2} = " + sp.latex(beta_m2))
    lines.append("")
    lines.append("Fixed points from β_λ=0:")
    lines.append("  Gaussian: λ*=0")
    lines.append("  Wilson–Fisher: λ* = " + sp.latex(wf))
    lines.append("  (numerical) λ* ≈ " + str(sp.N(wf.subs(subs_num))))
    lines.append("")
    lines.append("Linearized eigenvalues at (λ*, m^2=0):")
    lines.append("  Gaussian: " + ", ".join(map(sp.latex, evals_g)))
    lines.append("  Wilson–Fisher: " + ", ".join(map(sp.latex, evals_wf)))
    lines.append("  (numerical WF) " + ", ".join(str(sp.N(ev.subs(subs_num))) for ev in evals_wf))
    return "\n".join(lines)
def rg_rhs(eps: float, lam: np.ndarray, m2: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    c = 1.0 / (16.0 * np.pi**2)
    dlam = -eps * lam + 3.0 * c * lam**2
    dm2 = (-2.0 + c * lam) * m2
    return dlam, dm2


def integrate_rg(eps: float, lam0: float, m20: float, dt: float, steps: int) -> tuple[np.ndarray, np.ndarray]:
    lam = np.empty(steps + 1)
    m2 = np.empty(steps + 1)
    lam[0], m2[0] = lam0, m20
    for i in range(steps):
        dlam, dm2 = rg_rhs(eps, lam[i], m2[i])
        lam[i + 1] = lam[i] + dt * dlam
        m2[i + 1] = m2[i] + dt * dm2
        # guardrail: keep plot readable if flow runs away
        if abs(lam[i + 1]) > 200 or abs(m2[i + 1]) > 200:
            lam[i + 1 :] = lam[i + 1]
            m2[i + 1 :] = m2[i + 1]
            break
    return lam, m2
def make_plot(eps: float, outdir: Path, steps: int, dt: float, inits: list[tuple[float, float]]) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6.2, 4.4), dpi=140)

    # Vector field on a coarse grid
    lam_grid = np.linspace(0, max(0.5, max(l for l, _ in inits) * 1.4), 18)
    m2_grid = np.linspace(-1.0, 1.0, 18)
    L, M = np.meshgrid(lam_grid, m2_grid)
    dL, dM = rg_rhs(eps, L, M)
    speed = np.hypot(dL, dM) + 1e-12
    ax.quiver(L, M, dL / speed, dM / speed, speed, cmap="viridis", alpha=0.65, width=0.003)

    for lam0, m20 in inits:
        lam, m2 = integrate_rg(eps, lam0, m20, dt, steps)
        ax.plot(lam, m2, lw=2, label=f"(λ0={lam0:g}, m0^2={m20:g})")
        ax.scatter([lam[0]], [m2[0]], s=18)

    lam_star = 16 * np.pi**2 * eps / 3.0
    ax.axvline(lam_star, color="k", ls="--", lw=1, alpha=0.6, label="λ* (WF)")
    ax.set_title(rf"Toy RG flow in $(\lambda, m^2)$, $d=4-\epsilon$, $\epsilon={eps:g}$")
    ax.set_xlabel(r"$\lambda$")
    ax.set_ylabel(r"$m^2$")
    ax.set_xlim(lam_grid.min(), max(lam_grid.max(), lam_star * 1.05))
    ax.set_ylim(m2_grid.min(), m2_grid.max())
    ax.legend(fontsize=7, loc="upper right", frameon=True)
    ax.grid(True, alpha=0.25)

    outpath = outdir / f"rg_phi4_flow_eps{eps:g}.png"
    fig.tight_layout()
    fig.savefig(outpath)
    plt.close(fig)
    return outpath
def main() -> None:
    ap = argparse.ArgumentParser(description="Symbolic + toy numerical RG for φ^4 (one-loop).")
    ap.add_argument("--epsilon", type=float, default=1.0, help="ε in d=4-ε (default: 1 => 3D)")
    ap.add_argument("--steps", type=int, default=900)
    ap.add_argument("--dt", type=float, default=0.01, help="Euler step in RG time t")
    ap.add_argument("--outdir", type=Path, default=Path("outputs"), help="Directory to save plots")
    args = ap.parse_args()

    print(symbolic_report(args.epsilon))
    inits = [(0.2, 0.8), (0.2, -0.8), (1.0, 0.6), (2.0, -0.4), (4.0, 0.2)]
    outpath = make_plot(args.epsilon, args.outdir, args.steps, args.dt, inits)
    print(f"\nWROTE_PLOT:{outpath.as_posix()}")


if __name__ == "__main__":
    main()
