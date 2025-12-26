"""Cosmological observable calculators from model trajectories.

This module stays backend-agnostic: a *trajectory* is a mapping (dict-like)
containing time/efold series and/or horizon-exit values for key quantities.
Returned observables are plain dicts of floats suitable for downstream tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Dict
import numpy as np


def _get(traj: Mapping[str, Any], key: str, default: Any = None) -> Any:
    if key in traj:
        return traj[key]
    if default is not None:
        return default
    raise ValueError(f"trajectory missing required key '{key}'")


def _horizon_value(traj: Mapping[str, Any], name: str) -> float:
    """Best-effort: prefer '{name}_star', then last element of series '{name}'."""
    if f"{name}_star" in traj:
        return float(traj[f"{name}_star"])
    if name in traj:
        v = np.asarray(traj[name])
        return float(v[-1]) if v.ndim else float(v)
    raise ValueError(f"trajectory missing '{name}' or '{name}_star'")


@dataclass(frozen=True)
class ObservableSet:
    ns: float
    r: float
    alpha_s: float
    A_s: Optional[float] = None
    fNL_local: Optional[float] = None
    fNL_equil: Optional[float] = None
    reheating_Nre: Optional[float] = None
    reheating_Tre_GeV: Optional[float] = None
    tp_osc_amp: Optional[float] = None
    tp_osc_freq: Optional[float] = None
    w0: Optional[float] = None
    wa: Optional[float] = None

    def asdict(self) -> Dict[str, Optional[float]]:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}
def slow_roll_observables(traj: Mapping[str, Any]) -> Dict[str, float]:
    """Compute (n_s, r, alpha_s, A_s) from slow-roll style inputs.

    Expected keys (star = horizon-exit): eps_star, eta_star, xi2_star (optional),
    H_star (optional, for A_s), Mpl (optional, default 1).
    """
    eps = _horizon_value(traj, "eps")
    eta = _horizon_value(traj, "eta")
    xi2 = float(traj.get("xi2_star", traj.get("xi2", 0.0)))
    ns = 1.0 - 6.0 * eps + 2.0 * eta
    r = 16.0 * eps
    alpha_s = -24.0 * eps**2 + 16.0 * eps * eta - 2.0 * xi2
    out = {"ns": float(ns), "r": float(r), "alpha_s": float(alpha_s)}
    if "H_star" in traj or "H" in traj:
        H = _horizon_value(traj, "H")
        Mpl = float(traj.get("Mpl", 1.0))
        As = (H**2) / (8.0 * np.pi**2 * Mpl**2 * eps)
        out["A_s"] = float(As)
    return out


def non_gaussianity(traj: Mapping[str, Any]) -> Dict[str, float]:
    """Estimate leading f_NL amplitudes.

    - For canonical slow-roll, fNL_local ~ (5/12)(1-n_s).
    - For reduced sound speed c_s, equilateral fNL ~ (35/108)(c_s^{-2}-1).
    """
    sr = slow_roll_observables(traj)
    cs = float(traj.get("cs_star", traj.get("cs", 1.0)))
    f_local = (5.0 / 12.0) * (1.0 - sr["ns"])
    f_equil = (35.0 / 108.0) * (cs**-2 - 1.0) if cs > 0 else np.nan
    return {"fNL_local": float(f_local), "fNL_equil": float(f_equil), "cs": float(cs)}
def reheating_signatures(traj: Mapping[str, Any]) -> Dict[str, float]:
    """Compute simple reheating observables.

    Accepts: Nre (efolds during reheating) and/or rho_re, T_re_GeV, wre.
    If rho_re provided (in GeV^4), convert to T_re using g_* (default 100).
    """
    out: Dict[str, float] = {}
    if "Nre" in traj:
        out["reheating_Nre"] = float(traj["Nre"])
    if "T_re_GeV" in traj:
        out["reheating_Tre_GeV"] = float(traj["T_re_GeV"])
        return out
    if "rho_re" in traj:
        rho = float(traj["rho_re"])
        g = float(traj.get("gstar_re", 100.0))
        Tre = (30.0 * rho / (np.pi**2 * g)) ** 0.25
        out["reheating_Tre_GeV"] = float(Tre)
    return out


def transplanckian_signatures(traj: Mapping[str, Any]) -> Dict[str, float]:
    """Phenomenological trans-Planckian oscillation parameters.

    Uses beta_tp (Bogoliubov amplitude proxy) and scale ratio Lambda/H.
    Returns amplitude ~ 2|beta| and frequency ~ Lambda/H if available.
    """
    beta = float(traj.get("beta_tp", 0.0))
    lam_over_H = traj.get("Lambda_over_H", traj.get("Lambda_H", None))
    out = {"tp_osc_amp": float(2.0 * abs(beta))}
    if lam_over_H is not None:
        out["tp_osc_freq"] = float(lam_over_H)
    return out


def dark_energy_evolution(traj: Mapping[str, Any]) -> Dict[str, float]:
    """Late-time DE parameterization from w(a) series or w0/wa inputs.

    If provided w_of_a as (a, w) arrays, fit CPL: w(a)=w0+wa(1-a) by LSQ.
    """
    if "w0" in traj and "wa" in traj:
        return {"w0": float(traj["w0"]), "wa": float(traj["wa"])}
    if "w_of_a" not in traj:
        return {}
    a, w = traj["w_of_a"]
    a = np.asarray(a, dtype=float)
    w = np.asarray(w, dtype=float)
    X = np.column_stack([np.ones_like(a), (1.0 - a)])
    coef, *_ = np.linalg.lstsq(X, w, rcond=None)
    return {"w0": float(coef[0]), "wa": float(coef[1])}
def compute_observables(traj: Mapping[str, Any]) -> ObservableSet:
    """Compute a consolidated ObservableSet from a trajectory mapping."""
    sr = slow_roll_observables(traj)
    ng = non_gaussianity(traj)
    rh = reheating_signatures(traj)
    tp = transplanckian_signatures(traj)
    de = dark_energy_evolution(traj)
    return ObservableSet(
        ns=sr["ns"],
        r=sr["r"],
        alpha_s=sr["alpha_s"],
        A_s=sr.get("A_s"),
        fNL_local=ng.get("fNL_local"),
        fNL_equil=ng.get("fNL_equil"),
        reheating_Nre=rh.get("reheating_Nre"),
        reheating_Tre_GeV=rh.get("reheating_Tre_GeV"),
        tp_osc_amp=tp.get("tp_osc_amp"),
        tp_osc_freq=tp.get("tp_osc_freq"),
        w0=de.get("w0"),
        wa=de.get("wa"),
    )
