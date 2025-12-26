"""Discrete-gravity-inspired effective free-field models and observables.

This module provides (i) modified dispersion/propagators motivated by discrete
microstructure (causal sets, discrete spectra) and (ii) mappings to measurable
Gaussian correlators and simple entanglement diagnostics in analogue platforms.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
def coth(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    out = np.empty_like(x)
    small = np.abs(x) < 1e-6
    out[small] = 1.0 / x[small] + x[small] / 3.0  # series for stability
    out[~small] = np.cosh(x[~small]) / np.sinh(x[~small])
    return out


@dataclass(frozen=True)
class Dispersion:
    """Callable dispersion ω(k) with physical metadata."""

    name: str
    omega: Callable[[np.ndarray], np.ndarray]
    mass: float = 0.0
    params: tuple = ()

    def __call__(self, k: np.ndarray) -> np.ndarray:
        return self.omega(np.asarray(k, dtype=float))
def relativistic_dispersion(mass: float = 0.0, c: float = 1.0) -> Dispersion:
    def omega(k: np.ndarray) -> np.ndarray:
        return np.sqrt((c * k) ** 2 + mass**2)

    return Dispersion(name="relativistic", omega=omega, mass=mass, params=(c,))


def lifshitz_dispersion(
    mass: float = 0.0, c: float = 1.0, z: int = 2, k0: float = 1.0
) -> Dispersion:
    """ω^2 = m^2 + c^2 k^2 + (k/k0)^(2z) k0^2; mimics UV discreteness."""

    def omega(k: np.ndarray) -> np.ndarray:
        return np.sqrt(mass**2 + (c * k) ** 2 + (np.abs(k) / k0) ** (2 * z) * k0**2)

    return Dispersion(name=f"lifshitz_z{z}", omega=omega, mass=mass, params=(c, z, k0))


def causalset_like_dispersion(
    mass: float = 0.0, ell: float = 1.0, alpha: float = 1.0, p: int = 2
) -> Dispersion:
    """Smooth nonlocal/causal-set inspired UV correction.

    ω^2 = m^2 + k^2 * (1 + α (ℓ k)^p)/(1 + (ℓ k)^p), interpolating IR→UV.
    """

    def omega(k: np.ndarray) -> np.ndarray:
        kk = np.abs(k)
        u = (ell * kk) ** p
        eff = kk**2 * (1.0 + alpha * u) / (1.0 + u)
        return np.sqrt(mass**2 + eff)

    return Dispersion(name="causalset_like", omega=omega, mass=mass, params=(ell, alpha, p))
def finite_volume_modes_1d(L: float, nmax: int, periodic: bool = True) -> np.ndarray:
    """Discrete momenta k_n for a 1D box; periodic uses k=2πn/L."""
    n = np.arange(-nmax, nmax + 1, dtype=int)
    if periodic:
        return 2.0 * np.pi * n / L
    return np.pi * n / L  # e.g. Dirichlet/Neumann up to phase conventions


def thermal_occupation(omega: np.ndarray, T: float) -> np.ndarray:
    if T <= 0:
        return np.zeros_like(omega, dtype=float)
    x = omega / T
    x = np.clip(x, 1e-12, 7e2)
    return 1.0 / (np.exp(x) - 1.0)


def power_spectrum_equal_time(omega: np.ndarray, T: float = 0.0) -> np.ndarray:
    """P(k)=⟨|φ_k|^2⟩ for a free scalar at temperature T."""
    omega = np.asarray(omega, dtype=float)
    if T <= 0:
        return 1.0 / (2.0 * omega)
    return 0.5 / omega * coth(omega / (2.0 * T))
def wightman_1d_sum(
    dispersion: Dispersion,
    x: float,
    t: float,
    L: float,
    nmax: int,
    T: float = 0.0,
    periodic: bool = True,
) -> complex:
    """Finite-volume Wightman function in 1D from discrete mode sum."""
    k = finite_volume_modes_1d(L=L, nmax=nmax, periodic=periodic)
    w = dispersion(k)
    n = thermal_occupation(w, T)
    phase = np.exp(1j * k * x)
    term = (n + 1.0) * np.exp(-1j * w * t) + n * np.exp(1j * w * t)
    return np.sum(phase * term / (2.0 * w)) / L


def equal_time_correlators_1d(
    dispersion: Dispersion, x: float, L: float, nmax: int, T: float = 0.0
) -> tuple[float, float]:
    """Return (⟨φ(0)φ(x)⟩, ⟨π(0)π(x)⟩) at equal time in 1D finite volume."""
    k = finite_volume_modes_1d(L=L, nmax=nmax, periodic=True)
    w = dispersion(k)
    P = power_spectrum_equal_time(w, T)
    cxx = float(np.sum(np.cos(k * x) * P) / L)
    cpp = float(np.sum(np.cos(k * x) * (w**2) * P) / L)
    return cxx, cpp
def log_negativity_two_mode(cxx0: float, cpp0: float, cxx: float, cpp: float) -> float:
    """Logarithmic negativity for two equal-time modes of a stationary 1D Gaussian field.

    Assumes ⟨φπ⟩=0 and symmetric sites with local variances (cxx0, cpp0) and
    cross-correlations (cxx, cpp). Output in nats.
    """
    A = np.diag([cxx0, cpp0])
    C = np.diag([cxx, cpp])
    detA = float(np.linalg.det(A))
    detC = float(np.linalg.det(C))
    detV = float(np.linalg.det(np.block([[A, C], [C, A]])))
    delta_tilde = detA + detA - 2.0 * detC  # partial transpose flips sign of one momentum corr.
    # Symplectic eigenvalue of partially transposed state:
    nu_tilde = np.sqrt(0.5 * (delta_tilde - np.sqrt(max(delta_tilde**2 - 4.0 * detV, 0.0))))
    return float(max(0.0, -np.log(2.0 * nu_tilde)))


def entanglement_diagnostic_1d(
    dispersion: Dispersion, x: float, L: float, nmax: int, T: float = 0.0
) -> float:
    """Convenience wrapper: compute two-point log-negativity proxy vs separation x."""
    cxx0, cpp0 = equal_time_correlators_1d(dispersion, x=0.0, L=L, nmax=nmax, T=T)
    cxx, cpp = equal_time_correlators_1d(dispersion, x=x, L=L, nmax=nmax, T=T)
    return log_negativity_two_mode(cxx0, cpp0, cxx, cpp)
