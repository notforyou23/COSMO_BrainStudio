#!/usr/bin/env python3
\"\"\"Toy 2D Ising experiment: temperature + decoherence-like noise -> classicality diagnostics.

Runs Metropolis sampling on an LxL lattice with optional post-sweep bit-flip noise (p_noise),
then reports magnetization, energy, short-range correlations, a crude correlation-length proxy,
and single-site Shannon entropy. Produces a CSV and summary heatmaps.
\"\"\"
from __future__ import annotations
import argparse
from dataclasses import dataclass
from pathlib import Path
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def metropolis_sweep(spins: np.ndarray, beta: float, rng: np.random.Generator) -> None:
    L = spins.shape[0]
    for _ in range(L * L):
        i = rng.integers(0, L); j = rng.integers(0, L)
        s = spins[i, j]
        nn = spins[(i+1)%L, j] + spins[(i-1)%L, j] + spins[i, (j+1)%L] + spins[i, (j-1)%L]
        dE = 2.0 * s * nn
        if dE <= 0.0 or rng.random() < np.exp(-beta * dE):
            spins[i, j] = -s

def apply_noise(spins: np.ndarray, p: float, rng: np.random.Generator) -> None:
    if p <= 0: return
    mask = rng.random(spins.shape) < p
    spins[mask] *= -1

def energy_per_spin(spins: np.ndarray) -> float:
    right = np.roll(spins, -1, axis=1)
    down = np.roll(spins, -1, axis=0)
    E = -(spins * right + spins * down).sum()
    return E / spins.size

def corr_along_x(spins: np.ndarray, max_r: int) -> np.ndarray:
    c = []
    for r in range(1, max_r + 1):
        c.append(np.mean(spins * np.roll(spins, -r, axis=1)))
    return np.array(c, float)

def binary_entropy(p: float) -> float:
    p = float(np.clip(p, 1e-12, 1 - 1e-12))
    return -(p*np.log2(p) + (1-p)*np.log2(1-p))

def corr_length_proxy(c: np.ndarray) -> float:
    # Use ratio C(2)/C(1) if meaningful; else threshold at 1/e
    if len(c) >= 2 and c[0] > 1e-6 and c[1] > 1e-6 and c[1] < c[0]:
        return 1.0 / max(1e-6, np.log(c[0]/c[1]))
    thr = c[0]/np.e if len(c) else 0.0
    idx = np.where(c < thr)[0]
    return float(idx[0] + 1) if len(idx) else float(len(c))

@dataclass
class Params:
    L: int = 24
    sweeps_eq: int = 200
    sweeps_sample: int = 200
    thin: int = 2
    temps: int = 10
    tmin: float = 1.5
    tmax: float = 3.5
    noises: int = 6
    pmin: float = 0.0
    pmax: float = 0.15
    seed: int = 0
    outdir: Path = Path(\"outputs\")

def run(params: Params) -> pd.DataFrame:
    rng = np.random.default_rng(params.seed)
    Ts = np.linspace(params.tmin, params.tmax, params.temps)
    Ps = np.linspace(params.pmin, params.pmax, params.noises)
    rows = []
    for T in Ts:
        beta = 1.0 / T
        for p in Ps:
            spins = rng.choice(np.array([-1, 1], int), size=(params.L, params.L))
            for _ in range(params.sweeps_eq):
                metropolis_sweep(spins, beta, rng); apply_noise(spins, p, rng)
            mags = []; ens = []; ent1 = []; c1 = []; xi = []
            max_r = max(2, params.L // 4)
            for s in range(params.sweeps_sample):
                metropolis_sweep(spins, beta, rng); apply_noise(spins, p, rng)
                if s % params.thin: continue
                m = float(np.mean(spins))
                mags.append(abs(m))
                ens.append(energy_per_spin(spins))
                pup = 0.5 * (1.0 + m)
                ent1.append(binary_entropy(pup))
                c = corr_along_x(spins, max_r)
                c1.append(float(c[0]))
                xi.append(corr_length_proxy(c))
            rows.append(dict(T=T, p_noise=p, m_abs=np.mean(mags), e=np.mean(ens),
                             s1=np.mean(ent1), c1=np.mean(c1), xi=np.mean(xi)))
    return pd.DataFrame(rows)

def plot_heatmap(df: pd.DataFrame, x: str, y: str, z: str, path: Path, title: str) -> None:
    piv = df.pivot(index=y, columns=x, values=z).sort_index(ascending=True)
    plt.figure(figsize=(6.2, 4.5))
    im = plt.imshow(piv.values, origin=\"lower\", aspect=\"auto\",
                    extent=[piv.columns.min(), piv.columns.max(), piv.index.min(), piv.index.max()])
    plt.colorbar(im, label=z)
    plt.xlabel(x); plt.ylabel(y); plt.title(title)
    plt.tight_layout(); plt.savefig(path, dpi=160); plt.close()

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(\"--L\", type=int, default=24)
    ap.add_argument(\"--sweeps-eq\", type=int, default=200)
    ap.add_argument(\"--sweeps-sample\", type=int, default=200)
    ap.add_argument(\"--thin\", type=int, default=2)
    ap.add_argument(\"--temps\", type=int, default=10)
    ap.add_argument(\"--tmin\", type=float, default=1.5)
    ap.add_argument(\"--tmax\", type=float, default=3.5)
    ap.add_argument(\"--noises\", type=int, default=6)
    ap.add_argument(\"--pmin\", type=float, default=0.0)
    ap.add_argument(\"--pmax\", type=float, default=0.15)
    ap.add_argument(\"--seed\", type=int, default=0)
    ap.add_argument(\"--outdir\", type=Path, default=Path(\"outputs\"))
    args = ap.parse_args()
    params = Params(L=args.L, sweeps_eq=args.sweeps_eq, sweeps_sample=args.sweeps_sample,
                    thin=args.thin, temps=args.temps, tmin=args.tmin, tmax=args.tmax,
                    noises=args.noises, pmin=args.pmin, pmax=args.pmax,
                    seed=args.seed, outdir=args.outdir)
    tstamp = time.strftime(\"%Y%m%d_%H%M%S\")
    out = params.outdir / f\"toy_ising_emergent_classicality_{tstamp}\"
    out.mkdir(parents=True, exist_ok=True)
    df = run(params)
    df.to_csv(out / \"summary.csv\", index=False)
    plot_heatmap(df, \"T\", \"p_noise\", \"m_abs\", out / \"m_abs_heatmap.png\", \"|m| (order parameter)\")
    plot_heatmap(df, \"T\", \"p_noise\", \"s1\", out / \"s1_heatmap.png\", \"single-site Shannon entropy\")
    plot_heatmap(df, \"T\", \"p_noise\", \"xi\", out / \"xi_heatmap.png\", \"correlation length proxy\")
    print(f\"WROTE:{out}\")

if __name__ == \"__main__\":
    main()
