"""Toy Ising emergent classicality experiment.

This module is intentionally lightweight: it has deterministic defaults, avoids
heavy dependencies, and exposes a tiny API used by the benchmark pipeline.

Public API:
- ExperimentConfig: dataclass holding parameters.
- default_config(): returns a deterministic config.
- run_experiment(config=None): runs a small 1D Ising Monte Carlo and returns a
  JSON-serializable dict of observables.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from random import Random
from typing import Any, Dict, Optional, Union
@dataclass(frozen=True)
class ExperimentConfig:
    """Configuration for the toy 1D Ising experiment."""

    n_spins: int = 32
    temperature: float = 2.0
    coupling: float = 1.0  # J
    field: float = 0.0  # h
    sweeps: int = 200
    burn_in: int = 50
    seed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
def default_config() -> ExperimentConfig:
    """Return a deterministic default configuration."""
    return ExperimentConfig()
def _validate(cfg: ExperimentConfig) -> None:
    if cfg.n_spins <= 1:
        raise ValueError("n_spins must be > 1")
    if cfg.temperature <= 0:
        raise ValueError("temperature must be > 0")
    if cfg.sweeps <= 0:
        raise ValueError("sweeps must be > 0")
    if cfg.burn_in < 0 or cfg.burn_in >= cfg.sweeps:
        raise ValueError("burn_in must satisfy 0 <= burn_in < sweeps")
def _energy(spins: list[int], J: float, h: float) -> float:
    """Energy for periodic 1D Ising: E = -J sum s_i s_{i+1} - h sum s_i."""
    n = len(spins)
    pair = sum(spins[i] * spins[(i + 1) % n] for i in range(n))
    mag = sum(spins)
    return -J * pair - h * mag
def _metropolis_sweep(
    rng: Random, spins: list[int], beta: float, J: float, h: float
) -> None:
    n = len(spins)
    # Random sequential updates (n proposals per sweep)
    for _ in range(n):
        i = rng.randrange(n)
        s = spins[i]
        left = spins[(i - 1) % n]
        right = spins[(i + 1) % n]
        # Local energy change for flipping s -> -s
        dE = 2.0 * s * (J * (left + right) + h)
        if dE <= 0.0 or rng.random() < (2.718281828459045 ** (-beta * dE)):
            spins[i] = -s
def run_experiment(
    config: Optional[Union[ExperimentConfig, Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Run the toy experiment and return JSON-serializable results."""
    if config is None:
        cfg = default_config()
    elif isinstance(config, ExperimentConfig):
        cfg = config
    elif isinstance(config, dict):
        cfg = ExperimentConfig(**config)
    else:
        raise TypeError("config must be None, ExperimentConfig, or dict")

    _validate(cfg)
    rng = Random(cfg.seed)
    spins = [1 if rng.random() < 0.5 else -1 for _ in range(cfg.n_spins)]
    beta = 1.0 / cfg.temperature

    mags: list[float] = []
    energies: list[float] = []
    for sweep in range(cfg.sweeps):
        _metropolis_sweep(rng, spins, beta, cfg.coupling, cfg.field)
        if sweep >= cfg.burn_in:
            mags.append(sum(spins) / cfg.n_spins)
            energies.append(_energy(spins, cfg.coupling, cfg.field) / cfg.n_spins)

    # A simple "classicality" proxy: low magnetization variance indicates
    # stable macroscopic behavior (in this toy setting).
    if mags:
        m_mean = sum(mags) / len(mags)
        m2_mean = sum(m * m for m in mags) / len(mags)
        m_var = max(0.0, m2_mean - m_mean * m_mean)
    else:
        m_mean = 0.0
        m_var = 0.0

    e_mean = sum(energies) / len(energies) if energies else 0.0
    # Normalize to [0,1] with a soft scale to keep deterministic numbers.
    classicality = 1.0 / (1.0 + 10.0 * m_var)

    return {
        "experiment": "toy_ising_emergent_classicality",
        "config": cfg.to_dict(),
        "observables": {
            "magnetization_mean": m_mean,
            "magnetization_variance": m_var,
            "energy_per_spin_mean": e_mean,
            "classicality_score": classicality,
            "n_measurements": len(mags),
        },
    }
__all__ = ["ExperimentConfig", "default_config", "run_experiment"]
