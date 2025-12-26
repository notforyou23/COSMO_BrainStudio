"""Command-line entrypoint for reproducible toy experiments.

This module is intentionally lightweight: it manages seeding and output
directories and writes plots/tables deterministically for later inspection.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np
def _ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, header: Iterable[str], rows: Iterable[Iterable[Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(list(header))
        for r in rows:
            w.writerow(list(r))


def _rng(seed: int) -> np.random.Generator:
    # Centralized RNG creation so every experiment is deterministic given seed.
    return np.random.default_rng(int(seed))
def _savefig(path: Path) -> None:
    # Matplotlib import is intentionally delayed to keep import time low.
    import matplotlib.pyplot as plt  # type: ignore

    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _run_dir(root: Path, exp: str, seed: int, name: str | None) -> Path:
    # Deterministic path: avoids timestamps unless user supplies a name.
    run = f"{exp}_seed{seed}" + (f"_{name}" if name else "")
    return _ensure_dir(root / exp / run)
@dataclass(frozen=True)
class CommonArgs:
    out: Path
    seed: int
    name: str | None


def _common_parser(p: argparse.ArgumentParser) -> None:
    p.add_argument("--out", type=Path, default=Path("outputs"), help="Output root directory")
    p.add_argument("--seed", type=int, default=0, help="RNG seed (deterministic)")
    p.add_argument("--name", type=str, default=None, help="Optional run name suffix")
def exp_random_walk(args: argparse.Namespace) -> Path:
    """1D random walk ensemble; saves trajectory table and summary plot."""
    common = CommonArgs(out=args.out, seed=args.seed, name=args.name)
    run = _run_dir(common.out, "random_walk", common.seed, common.name)
    rng = _rng(common.seed)

    steps = int(args.steps)
    n = int(args.n)
    # Steps are +/-1; positions include x0=0 so length steps+1.
    jumps = rng.choice([-1, 1], size=(n, steps))
    x = np.cumsum(jumps, axis=1)
    x = np.concatenate([np.zeros((n, 1), dtype=int), x], axis=1)

    _write_csv(run / "trajectories.csv", ["traj", "t", "x"], ((i, t, int(x[i, t])) for i in range(n) for t in range(steps + 1)))
    summary = {
        "experiment": "random_walk",
        "seed": common.seed,
        "steps": steps,
        "n": n,
        "final_mean": float(np.mean(x[:, -1])),
        "final_var": float(np.var(x[:, -1])),
    }
    _write_json(run / "summary.json", summary)
    _write_json(run / "args.json", {**asdict(common), "steps": steps, "n": n})

    import matplotlib.pyplot as plt  # type: ignore

    t = np.arange(steps + 1)
    for i in range(min(n, 20)):
        plt.plot(t, x[i], alpha=0.5, lw=1)
    plt.xlabel("t")
    plt.ylabel("x(t)")
    plt.title("1D random walk (first 20 trajectories)")
    _savefig(run / "trajectories.png")

    plt.hist(x[:, -1], bins=25, density=True)
    plt.xlabel("x(T)")
    plt.ylabel("density")
    plt.title("Final position distribution")
    _savefig(run / "final_hist.png")
    return run
def _ent_entropy_two_qubit_state(psi: np.ndarray) -> float:
    # psi is shape (4,), pure state on A(2) x B(2).
    psi = psi / np.linalg.norm(psi)
    rho = np.outer(psi, np.conjugate(psi))  # 4x4
    # partial trace over B:
    rho_a = np.zeros((2, 2), dtype=complex)
    for b in range(2):
        idx = [2 * 0 + b, 2 * 1 + b]
        rho_a += rho[np.ix_(idx, idx)]
    evals = np.linalg.eigvalsh(rho_a).real
    evals = np.clip(evals, 0.0, 1.0)
    nz = evals[evals > 0]
    return float(-np.sum(nz * np.log2(nz)))


def exp_two_qubit_entanglement(args: argparse.Namespace) -> Path:
    """Samples random two-qubit pure states and plots entanglement entropy."""
    common = CommonArgs(out=args.out, seed=args.seed, name=args.name)
    run = _run_dir(common.out, "two_qubit_entanglement", common.seed, common.name)
    rng = _rng(common.seed)

    n = int(args.n)
    # Complex Gaussian -> Haar-random direction after normalization.
    psi = rng.normal(size=(n, 4)) + 1j * rng.normal(size=(n, 4))
    ent = np.array([_ent_entropy_two_qubit_state(psi[i]) for i in range(n)], dtype=float)

    _write_csv(run / "entropies.csv", ["i", "S_bits"], ((i, float(ent[i])) for i in range(n)))
    _write_json(run / "summary.json", {"experiment": "two_qubit_entanglement", "seed": common.seed, "n": n, "mean_S": float(ent.mean())})
    _write_json(run / "args.json", {**asdict(common), "n": n})

    import matplotlib.pyplot as plt  # type: ignore

    plt.hist(ent, bins=30, range=(0, 1), density=True)
    plt.xlabel("S(ρ_A) [bits]")
    plt.ylabel("density")
    plt.title("Entanglement entropy of random two-qubit pure states")
    _savefig(run / "entropy_hist.png")
    return run
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="toy-exp", description="Reproducible toy-model experiments (numerical/symbolic).")
    sub = p.add_subparsers(dest="experiment", required=True)

    p_rw = sub.add_parser("random-walk", help="1D random walk ensemble")
    _common_parser(p_rw)
    p_rw.add_argument("--steps", type=int, default=200)
    p_rw.add_argument("--n", type=int, default=200)
    p_rw.set_defaults(_fn=exp_random_walk)

    p_ent = sub.add_parser("two-qubit-entanglement", help="Entanglement entropy of random two-qubit states")
    _common_parser(p_ent)
    p_ent.add_argument("--n", type=int, default=5000)
    p_ent.set_defaults(_fn=exp_two_qubit_entanglement)
    return p


def main(argv: List[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run = args._fn(args)
    print(str(run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
