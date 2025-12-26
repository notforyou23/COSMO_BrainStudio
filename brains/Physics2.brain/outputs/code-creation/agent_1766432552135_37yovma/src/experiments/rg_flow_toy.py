"""Toy renormalization-group (RG) flow experiment: 1D Ising decimation.

We consider the zero-field 1D Ising model with coupling K = beta * J.
Decimating every other spin (block size b=2) yields the exact map:
    K' = 0.5 * log(cosh(2K))
(up to an additive constant in the free energy, which we ignore).

This script generates:
- A table (CSV) of K, K', and beta(K)=K'-K over a grid.
- A beta-function plot and example flow trajectories (PNG).

Run:
  python -m src.experiments.rg_flow_toy --out outputs/rg_toy
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np


def rg_map(K: np.ndarray) -> np.ndarray:
    """Exact decimation map for 1D Ising coupling K."""
    K = np.asarray(K, dtype=float)
    return 0.5 * np.log(np.cosh(2.0 * K))


def beta_function(K: np.ndarray) -> np.ndarray:
    """Discrete beta function for b=2: beta(K) = K' - K."""
    return rg_map(K) - np.asarray(K, dtype=float)


def iterate_flow(K0: float, n_steps: int) -> np.ndarray:
    """Iterate RG map starting at K0."""
    Ks = [float(K0)]
    K = float(K0)
    for _ in range(n_steps):
        K = float(rg_map(K))
        Ks.append(K)
    return np.array(Ks, dtype=float)


@dataclass(frozen=True)
class Config:
    out: str
    n_grid: int = 301
    k_max: float = 3.0
    n_steps: int = 12
    n_traj: int = 7
    seed: int = 0


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _write_csv(path: Path, rows: Iterable[Dict[str, float]]) -> None:
    rows = list(rows)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def make_plots(out_dir: Path, grid_K: np.ndarray, Kp: np.ndarray, beta: np.ndarray, trajs: List[np.ndarray]) -> None:
    import matplotlib.pyplot as plt

    # Beta-function plot
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(grid_K, beta, lw=2)
    ax.axhline(0.0, color="k", lw=1)
    ax.set_xlabel(r"Coupling $K$")
    ax.set_ylabel(r"$\beta(K)=K'-K$")
    ax.set_title("1D Ising decimation: discrete beta function (b=2)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "rg_beta.png", dpi=160)
    plt.close(fig)

    # Flow trajectories K_n vs step
    fig, ax = plt.subplots(figsize=(6, 4))
    for Ks in trajs:
        ax.plot(np.arange(len(Ks)), Ks, marker="o", ms=3)
    ax.set_xlabel("RG step n")
    ax.set_ylabel(r"$K_n$")
    ax.set_title("RG flow trajectories under decimation")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "flow_trajectories.png", dpi=160)
    plt.close(fig)

    # K' vs K with diagonal
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot(grid_K, Kp, lw=2, label=r"$K' = f(K)$")
    ax.plot(grid_K, grid_K, lw=1, color="k", alpha=0.7, label=r"$K'=K$")
    ax.set_xlabel(r"$K$")
    ax.set_ylabel(r"$K'$")
    ax.set_title("RG map (fixed points at intersections)")
    ax.legend(frameon=False)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "rg_map.png", dpi=160)
    plt.close(fig)


def run(cfg: Config) -> Dict[str, str]:
    out_dir = Path(cfg.out)
    _ensure_dir(out_dir)

    rng = np.random.default_rng(cfg.seed)
    grid_K = np.linspace(0.0, float(cfg.k_max), int(cfg.n_grid))
    Kp = rg_map(grid_K)
    beta = Kp - grid_K

    rows = ({"K": float(k), "K_prime": float(kp), "beta": float(b)} for k, kp, b in zip(grid_K, Kp, beta))
    _write_csv(out_dir / "rg_table.csv", rows)

    # Pick some initial couplings for trajectories (include small and moderate K)
    K0s = np.r_[np.linspace(0.05, 0.6, cfg.n_traj // 2), np.linspace(0.8, min(2.5, cfg.k_max), cfg.n_traj - cfg.n_traj // 2)]
    K0s = (K0s + 0.02 * rng.normal(size=K0s.shape)).clip(0.0, cfg.k_max)
    trajs = [iterate_flow(float(k0), int(cfg.n_steps)) for k0 in K0s]

    make_plots(out_dir, grid_K, Kp, beta, trajs)

    # Small-K linearization slope: f(K) ~ a K^2 (no linear term) for this map
    # Estimate numerically by fitting log(f(K)) ~ log(a) + 2 log(K) over small K.
    small = grid_K[1:40]
    loga = np.mean(np.log(rg_map(small) / (small**2 + 1e-300)))
    a_est = float(np.exp(loga))

    meta = {
        "config": asdict(cfg),
        "notes": "1D Ising, zero field, exact decimation map K' = 0.5*log(cosh(2K)).",
        "fixed_points": {"K=0": "stable", "K->infty": "stable (flows upward for large K)"},
        "small_K_asymptotic": {"f(K) ~ a K^2": a_est},
        "artifacts": ["rg_table.csv", "rg_beta.png", "flow_trajectories.png", "rg_map.png"],
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {"out_dir": str(out_dir)}


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=str, required=True, help="Output directory.")
    p.add_argument("--n-grid", type=int, default=Config.n_grid)
    p.add_argument("--k-max", type=float, default=Config.k_max)
    p.add_argument("--n-steps", type=int, default=Config.n_steps)
    p.add_argument("--n-traj", type=int, default=Config.n_traj)
    p.add_argument("--seed", type=int, default=Config.seed)
    return p


def main(argv: List[str] | None = None) -> None:
    args = build_argparser().parse_args(argv)
    cfg = Config(out=args.out, n_grid=args.n_grid, k_max=args.k_max, n_steps=args.n_steps, n_traj=args.n_traj, seed=args.seed)
    info = run(cfg)
    print(json.dumps(info))


if __name__ == "__main__":
    main()
