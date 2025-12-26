"""Toy lattice/graph decoherence experiment.

Model: one system qubit coupled (sigma_z ⊗ sigma_z) to an N-site environment
chain with weak nearest-neighbor XX interactions. Starting from a global pure
state, the reduced system state decoheres and its entropy tracks system-env
entanglement.

Run:
  python -m src.experiments.toy_lattice_decoherence --help
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np


# --- small dense-qubit utilities (N <= ~9 is fine) ---
I2 = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)


def kron(ops):
    out = ops[0]
    for op in ops[1:]:
        out = np.kron(out, op)
    return out


def op_on(n, i, op):
    ops = [I2] * n
    ops[i] = op
    return kron(ops)


def two_body(n, i, j, opi, opj):
    ops = [I2] * n
    ops[i], ops[j] = opi, opj
    return kron(ops)


def ptrace_env(rho, n_sys=1):
    """Trace out environment qubits from a (2^N x 2^N) density matrix."""
    n = int(np.log2(rho.shape[0]))
    dS, dE = 2**n_sys, 2 ** (n - n_sys)
    r = rho.reshape(dS, dE, dS, dE)
    return np.einsum("a b c b -> a c", r)


def von_neumann_entropy(rho, eps=1e-12):
    w = np.linalg.eigvalsh((rho + rho.conj().T) / 2)
    w = np.clip(w.real, eps, 1.0)
    return float(-(w * np.log2(w)).sum())


def unitary_from_h(H, t):
    w, v = np.linalg.eigh(H)
    return v @ np.diag(np.exp(-1j * w * t)) @ v.conj().T


@dataclass
class Results:
    t: np.ndarray
    coherence: np.ndarray
    purity: np.ndarray
    entropy: np.ndarray


def simulate(n_env=5, g=1.0, j=0.2, t_max=12.0, n_t=200) -> Results:
    """Evolve |+>_S ⊗ |+...+>_E under H and compute reduced-state diagnostics."""
    n = 1 + n_env  # total qubits, system is site 0
    # Hamiltonian: env XX chain + system-env ZZ couplings (graph: star from system)
    H = np.zeros((2**n, 2**n), dtype=complex)
    for k in range(1, n):  # system-env coupling
        H += g * two_body(n, 0, k, Z, Z)
    for k in range(1, n - 1):  # env chain interactions
        H += j * two_body(n, k, k + 1, X, X)  # env XX chain
    # initial state |+>^{⊗n}
    plus = (np.array([1.0, 1.0], dtype=complex) / np.sqrt(2))
    psi0 = kron([plus] * n)
    rho0 = np.outer(psi0, psi0.conj())

    t = np.linspace(0.0, float(t_max), int(n_t))
    coh = np.empty_like(t)
    pur = np.empty_like(t)
    ent = np.empty_like(t)
    for idx, ti in enumerate(t):
        U = unitary_from_h(H, ti)
        rho = U @ rho0 @ U.conj().T
        rhoS = ptrace_env(rho, n_sys=1)
        coh[idx] = abs(rhoS[0, 1]) * 2  # normalized: 1 at t=0 for |+>
        pur[idx] = float(np.real(np.trace(rhoS @ rhoS)))
        ent[idx] = von_neumann_entropy(rhoS)
    return Results(t=t, coherence=coh, purity=pur, entropy=ent)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--n-env", type=int, default=5)
    p.add_argument("--g", type=float, default=1.0, help="system-env ZZ strength")
    p.add_argument("--j", type=float, default=0.2, help="env XX coupling")
    p.add_argument("--t-max", type=float, default=12.0)
    p.add_argument("--n-t", type=int, default=200)
    p.add_argument("--outdir", type=Path, default=Path("outputs/toy_lattice_decoherence"))
    args = p.parse_args(argv)

    args.outdir.mkdir(parents=True, exist_ok=True)
    res = simulate(args.n_env, args.g, args.j, args.t_max, args.n_t)

    # Save a quick table and a plot illustrating decoherence + entanglement growth.
    import matplotlib.pyplot as plt  # optional dependency at runtime

    fig, ax = plt.subplots(2, 1, sharex=True, figsize=(7, 5))
    ax[0].plot(res.t, res.coherence, label="|rho01| normalized")
    ax[0].set_ylabel("coherence")
    ax[0].set_ylim(0, 1.05)
    ax[0].grid(True, alpha=0.3)
    ax[1].plot(res.t, res.entropy, color="C1", label="S(ρ_S)")
    ax[1].set_xlabel("time")
    ax[1].set_ylabel("entropy (bits)")
    ax[1].set_ylim(0, 1.05)
    ax[1].grid(True, alpha=0.3)
    fig.suptitle(f"Toy decoherence: n_env={args.n_env}, g={args.g}, j={args.j}")
    fig.tight_layout()
    fig.savefig(args.outdir / "decoherence_entropy.png", dpi=160)

    csv_path = args.outdir / "timeseries.csv"
    data = np.c_[res.t, res.coherence, res.purity, res.entropy]
    header = "t,coherence,purity,entropy_bits"
    np.savetxt(csv_path, data, delimiter=",", header=header, comments="")
    # Small parameter sweep summary (illustrates coupling-strength dependence)
    sweep_g = [0.0, args.g / 2, args.g, 2 * args.g]
    rows = []
    for gi in sweep_g:
        r = simulate(args.n_env, gi, args.j, args.t_max, max(60, args.n_t // 3))
        rows.append((gi, float(r.coherence[-1]), float(r.entropy[-1])))
    summary_path = args.outdir / "summary_g_sweep.csv"
    np.savetxt(summary_path, np.array(rows), delimiter=",", header="g,final_coherence,final_entropy_bits", comments="")

    print(f"WROTE {csv_path} and {summary_path} and decoherence_entropy.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
