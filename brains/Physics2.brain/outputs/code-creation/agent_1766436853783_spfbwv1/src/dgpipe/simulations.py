"""dgpipe.simulations

Controlled numerical + semi-analytical simulators used to quantify finite-size,
discretization, and dispersive systematics for measurement protocols and to
produce synthetic datasets for inference tests.

The models here are intentionally lightweight: a free scalar field in 1D with
periodic boundary conditions and a causal-set/discrete-microstructure inspired
modified dispersion relation.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, Literal, Mapping, Optional, Tuple

import numpy as np


ProtocolName = Literal[
    "equal_time_correlator",
    "time_correlator",
    "logneg_two_mode",
]
@dataclass(frozen=True)
class DiscreteParams:
    """Parameters encoding discrete microstructure effects.

    alpha, power: control a leading-order dispersive correction
        omega(k) = sqrt(k^2 + m^2) * (1 + alpha * (a|k|)^power)
    a: microscopic length/spacing, also sets UV cutoff k_max ~ pi/a.
    """

    a: float = 1.0
    alpha: float = 0.0
    power: int = 2
    m: float = 0.0


@dataclass(frozen=True)
class SimConfig:
    """Finite-size/discretization controls."""

    L: float = 64.0          # system length
    N_modes: int = 256       # number of Fourier modes (finite-size)
    k_cut: Optional[float] = None  # optional additional cutoff (<= pi/a)


@dataclass(frozen=True)
class NoiseModel:
    """Simple i.i.d. Gaussian measurement noise."""

    sigma: float = 1e-3
    seed: int = 0
def _k_grid(cfg: SimConfig, dp: DiscreteParams) -> np.ndarray:
    n = np.arange(-cfg.N_modes // 2, cfg.N_modes // 2, dtype=float)
    k = 2.0 * np.pi * n / cfg.L
    k_max = np.pi / max(dp.a, 1e-12)
    if cfg.k_cut is not None:
        k_max = min(k_max, float(cfg.k_cut))
    return k[np.abs(k) <= k_max]


def _omega(k: np.ndarray, dp: DiscreteParams) -> np.ndarray:
    w0 = np.sqrt(k * k + dp.m * dp.m)
    corr = 1.0 + dp.alpha * np.power(dp.a * np.abs(k), dp.power)
    return w0 * corr


def _wightman(t: float, x: np.ndarray, cfg: SimConfig, dp: DiscreteParams) -> np.ndarray:
    """Discrete-mode approximation to <phi(t,x) phi(0,0)> in vacuum."""
    k = _k_grid(cfg, dp)
    w = _omega(k, dp)
    phase = np.outer(k, x) - (w[:, None] * t)
    # (1/L) sum_k (e^{i(kx - wt)})/(2w)
    return (np.cos(phase) / (2.0 * w[:, None])).sum(axis=0) / cfg.L


def _pi_pi(t: float, x: np.ndarray, cfg: SimConfig, dp: DiscreteParams) -> np.ndarray:
    """Discrete-mode approximation to <pi(t,x) pi(0,0)> with pi=dot(phi)."""
    k = _k_grid(cfg, dp)
    w = _omega(k, dp)
    phase = np.outer(k, x) - (w[:, None] * t)
    return ((w[:, None] * np.cos(phase)) / 2.0).sum(axis=0) / cfg.L
def _add_noise(y: np.ndarray, noise: NoiseModel) -> Tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(noise.seed)
    eps = rng.normal(0.0, noise.sigma, size=y.shape)
    return y + eps, np.full_like(y, noise.sigma, dtype=float)


def simulate_equal_time_correlator(
    x: Iterable[float],
    *,
    cfg: SimConfig,
    dp: DiscreteParams,
    noise: Optional[NoiseModel] = None,
) -> Dict[str, Any]:
    x = np.asarray(list(x), dtype=float)
    y = _wightman(0.0, x, cfg, dp)
    if noise is not None:
        y, yerr = _add_noise(y, noise)
    else:
        yerr = np.zeros_like(y)
    return {
        "protocol": "equal_time_correlator",
        "x": x.tolist(),
        "t": 0.0,
        "y": y.tolist(),
        "yerr": yerr.tolist(),
        "meta": {"sim": asdict(cfg), "discrete": asdict(dp), "noise": None if noise is None else asdict(noise)},
    }


def simulate_time_correlator(
    t: Iterable[float],
    *,
    x: float = 0.0,
    cfg: SimConfig,
    dp: DiscreteParams,
    noise: Optional[NoiseModel] = None,
) -> Dict[str, Any]:
    t = np.asarray(list(t), dtype=float)
    y = np.array([_wightman(float(tt), np.array([x]), cfg, dp)[0] for tt in t], dtype=float)
    if noise is not None:
        y, yerr = _add_noise(y, noise)
    else:
        yerr = np.zeros_like(y)
    return {
        "protocol": "time_correlator",
        "x": float(x),
        "t": t.tolist(),
        "y": y.tolist(),
        "yerr": yerr.tolist(),
        "meta": {"sim": asdict(cfg), "discrete": asdict(dp), "noise": None if noise is None else asdict(noise)},
    }
def _symplectic_eigs_2mode(V: np.ndarray) -> np.ndarray:
    """Symplectic eigenvalues for a 4x4 two-mode covariance matrix."""
    if V.shape != (4, 4):
        raise ValueError("V must be 4x4")
    A, B, C = V[:2, :2], V[2:, 2:], V[:2, 2:]
    detA, detB, detC, detV = np.linalg.det(A), np.linalg.det(B), np.linalg.det(C), np.linalg.det(V)
    Delta = detA + detB + 2.0 * detC
    rad = max(0.0, Delta * Delta - 4.0 * detV)
    nu1 = np.sqrt(max(0.0, (Delta + np.sqrt(rad)) / 2.0))
    nu2 = np.sqrt(max(0.0, (Delta - np.sqrt(rad)) / 2.0))
    return np.array([nu1, nu2], dtype=float)


def simulate_logneg_two_mode(
    x1: float,
    x2: float,
    *,
    cfg: SimConfig,
    dp: DiscreteParams,
    noise: Optional[NoiseModel] = None,
) -> Dict[str, Any]:
    """Two-mode logarithmic negativity from field/pi correlators at two points.

    Uses a Gaussian-state (free field) covariance matrix with quadratures
    (q1,p1,q2,p2). Partial transpose corresponds to p2 -> -p2.
    """
    xs = np.array([0.0, abs(x2 - x1)], dtype=float)
    qq = _wightman(0.0, xs, cfg, dp)
    pp = _pi_pi(0.0, xs, cfg, dp)
    # Covariance matrix: V_ij = <{R_i,R_j}>/2 with cross qp set to 0 (vacuum, equal time)
    V = np.zeros((4, 4), dtype=float)
    V[0, 0] = qq[0]
    V[2, 2] = qq[0]
    V[0, 2] = V[2, 0] = qq[1]
    V[1, 1] = pp[0]
    V[3, 3] = pp[0]
    V[1, 3] = V[3, 1] = pp[1]

    # Partial transpose on mode 2: flip sign of p2 correlations => Lambda=diag(1,1,1,-1)
    Lambda = np.diag([1.0, 1.0, 1.0, -1.0])
    Vpt = Lambda @ V @ Lambda
    nus = _symplectic_eigs_2mode(Vpt)
    nu_min = float(np.min(nus))
    logneg = max(0.0, -np.log(2.0 * nu_min))

    y = np.array([logneg], dtype=float)
    if noise is not None:
        y, yerr = _add_noise(y, noise)
        logneg = float(y[0])
        logneg_err = float(yerr[0])
    else:
        logneg_err = 0.0
    return {
        "protocol": "logneg_two_mode",
        "x1": float(x1),
        "x2": float(x2),
        "y": logneg,
        "yerr": logneg_err,
        "meta": {"sim": asdict(cfg), "discrete": asdict(dp), "noise": None if noise is None else asdict(noise)},
    }
def run_protocol(
    protocol: ProtocolName,
    *,
    grid: Iterable[float] = (),
    x: float = 0.0,
    x1: float = 0.0,
    x2: float = 1.0,
    cfg: Optional[SimConfig] = None,
    dp: Optional[DiscreteParams] = None,
    noise: Optional[NoiseModel] = None,
) -> Dict[str, Any]:
    """Unified entrypoint used by the pipeline/CLI.

    grid means x-grid for equal-time correlator and t-grid for time correlator.
    """
    cfg = SimConfig() if cfg is None else cfg
    dp = DiscreteParams() if dp is None else dp
    if protocol == "equal_time_correlator":
        return simulate_equal_time_correlator(grid, cfg=cfg, dp=dp, noise=noise)
    if protocol == "time_correlator":
        return simulate_time_correlator(grid, x=x, cfg=cfg, dp=dp, noise=noise)
    if protocol == "logneg_two_mode":
        return simulate_logneg_two_mode(x1, x2, cfg=cfg, dp=dp, noise=noise)
    raise ValueError(f"Unknown protocol: {protocol}")


def sweep_systematics(
    protocol: ProtocolName,
    *,
    grid: Iterable[float],
    cfgs: Iterable[SimConfig],
    dp: DiscreteParams,
    noise: Optional[NoiseModel] = None,
) -> Dict[str, Any]:
    """Run a controlled sweep over finite-size/discretization configurations."""
    out = []
    for i, cfg in enumerate(cfgs):
        nm = None if noise is None else NoiseModel(sigma=noise.sigma, seed=noise.seed + i)
        out.append(run_protocol(protocol, grid=grid, cfg=cfg, dp=dp, noise=nm))
    return {"protocol": protocol, "dp": asdict(dp), "runs": out}
