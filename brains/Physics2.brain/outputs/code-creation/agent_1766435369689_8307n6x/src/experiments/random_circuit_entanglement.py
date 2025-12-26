"""Random circuit entanglement growth toy experiment.

Simulates a 1D brickwork random unitary circuit on n qubits (statevector),
tracking bipartite entanglement entropy across the middle cut vs depth.
Produces a saved figure and prints a small summary table.

Run:
  python -m src.experiments.random_circuit_entanglement --n 8 --depth 40 --samples 32
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np


def haar_unitary(dim: int, rng: np.random.Generator) -> np.ndarray:
    """Sample a Haar-random unitary via QR decomposition."""
    z = (rng.normal(size=(dim, dim)) + 1j * rng.normal(size=(dim, dim))) / np.sqrt(2.0)
    q, r = np.linalg.qr(z)
    ph = np.diag(r) / np.abs(np.diag(r))
    return q * ph


def apply_two_qubit_gate(state: np.ndarray, U: np.ndarray, i: int, n: int) -> np.ndarray:
    """Apply 2-qubit gate U to qubits (i, i+1) in an n-qubit statevector."""
    psi = state.reshape([2] * n)
    axes = list(range(n))
    axes[i], axes[-2] = axes[-2], axes[i]
    axes[i + 1], axes[-1] = axes[-1], axes[i + 1]
    tmp = np.transpose(psi, axes).reshape(-1, 4)
    tmp = tmp @ U.T  # act on last two indices
    psi2 = tmp.reshape([2] * n)
    inv = np.argsort(axes)
    return np.transpose(psi2, inv).reshape(-1)


def entanglement_entropy_midcut(state: np.ndarray, n: int) -> float:
    """Von Neumann entropy S(ρ_A) across the middle cut in bits."""
    na = n // 2
    psi = state.reshape(2**na, 2 ** (n - na))
    s = np.linalg.svd(psi, compute_uv=False)
    p = (s**2).real
    p = p[p > 1e-15]
    return float(-(p * np.log2(p)).sum())


@dataclass(frozen=True)
class Result:
    depth: np.ndarray
    mean_S: np.ndarray
    std_S: np.ndarray
    sat_value: float
def run_experiment(n: int, depth: int, samples: int, seed: int) -> Result:
    rng = np.random.default_rng(seed)
    depths = np.arange(depth + 1)
    ent = np.zeros((samples, depth + 1), dtype=float)

    for s in range(samples):
        state = np.zeros(2**n, dtype=complex)
        state[0] = 1.0
        ent[s, 0] = entanglement_entropy_midcut(state, n)
        for t in range(1, depth + 1):
            parity = (t - 1) % 2
            for i in range(parity, n - 1, 2):
                U = haar_unitary(4, rng)
                state = apply_two_qubit_gate(state, U, i, n)
            ent[s, t] = entanglement_entropy_midcut(state, n)

    mean_S = ent.mean(axis=0)
    std_S = ent.std(axis=0, ddof=1) if samples > 1 else np.zeros_like(mean_S)
    sat_value = float(mean_S[-max(3, depth // 5) :].mean())
    return Result(depth=depths, mean_S=mean_S, std_S=std_S, sat_value=sat_value)


def save_plot(res: Result, n: int, outpath: Path) -> None:
    import matplotlib.pyplot as plt

    plt.figure(figsize=(6.0, 3.8))
    plt.plot(res.depth, res.mean_S, lw=2.0, label="mean S(midcut)")
    if np.any(res.std_S > 0):
        plt.fill_between(
            res.depth,
            res.mean_S - res.std_S,
            res.mean_S + res.std_S,
            alpha=0.25,
            linewidth=0.0,
            label="±1 std",
        )
    plt.axhline(n // 2, ls="--", lw=1.0, color="k", alpha=0.5, label="max (=n/2)")
    plt.xlabel("Circuit depth (layers)")
    plt.ylabel("Entanglement entropy S (bits)")
    plt.title(f"Random brickwork circuit entanglement (n={n})")
    plt.legend(frameon=False, fontsize=9)
    plt.tight_layout()
    outpath.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(outpath, dpi=160)
    plt.close()
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--n", type=int, default=8, help="number of qubits (even recommended)")
    p.add_argument("--depth", type=int, default=40, help="number of circuit layers")
    p.add_argument("--samples", type=int, default=32, help="Monte Carlo samples")
    p.add_argument("--seed", type=int, default=0, help="RNG seed")
    p.add_argument("--outdir", type=Path, default=Path("outputs"), help="output directory")
    args = p.parse_args(argv)

    if args.n < 2 or args.depth < 1 or args.samples < 1:
        raise SystemExit("Require n>=2, depth>=1, samples>=1")

    res = run_experiment(args.n, args.depth, args.samples, args.seed)
    outpath = args.outdir / f"random_circuit_entanglement_n{args.n}_d{args.depth}_s{args.samples}.png"
    save_plot(res, args.n, outpath)

    maxS = args.n // 2
    checkpoints = [0, 1, 2, 5, 10, args.depth]
    checkpoints = sorted({c for c in checkpoints if 0 <= c <= args.depth})
    print(f"Saved figure: {outpath}")
    print(f"Estimated saturation: {res.sat_value:.3f} bits (max {maxS})")
    print("Depth  MeanS  StdS")
    for d in checkpoints:
        print(f"{d:>5d}  {res.mean_S[d]:>5.3f}  {res.std_S[d]:>5.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
