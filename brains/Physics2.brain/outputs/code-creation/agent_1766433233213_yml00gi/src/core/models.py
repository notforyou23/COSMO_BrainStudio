"""Model-specific cosmology backends with lightweight observable calculators.

This module provides compact, model-level maps from theory parameters to
cosmological observables used elsewhere for conjecture/constraint tests.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import exp, log, pi, sin
from typing import Any, Dict, Mapping, Optional
@dataclass(frozen=True)
class ModelResult:
    name: str
    params: Dict[str, Any]
    observables: Dict[str, float]
    meta: Dict[str, Any] = field(default_factory=dict)
class BaseCosmoModel:
    """Base interface: subclasses implement `compute_observables`."""

    name: str = "base"

    def __init__(self, **params: Any) -> None:
        self.params = dict(params)

    def compute_observables(self) -> Dict[str, float]:
        raise NotImplementedError

    def run(self) -> ModelResult:
        obs = self.compute_observables()
        return ModelResult(self.name, dict(self.params), obs, meta={})
def _sr_from_N(p: float, N: float) -> Dict[str, float]:
    # Monomial slow-roll (V ∝ φ^p) at horizon exit.
    ns = 1.0 - (p + 2.0) / (2.0 * N)
    r = 4.0 * p / N
    alpha_s = -(p + 2.0) / (2.0 * N * N)
    return {"ns": ns, "r": r, "alpha_s": alpha_s}

def _starobinsky_from_N(N: float) -> Dict[str, float]:
    ns = 1.0 - 2.0 / N
    r = 12.0 / (N * N)
    alpha_s = -2.0 / (N * N)
    return {"ns": ns, "r": r, "alpha_s": alpha_s}

def _single_field_fnl(ns: float, r: float) -> Dict[str, float]:
    # Standard consistency estimates (order-of-magnitude, model-agnostic).
    f_local = (5.0 / 12.0) * (1.0 - ns)
    f_eq = 0.1 * (r / 16.0)  # O(ε)
    return {"fNL_local": f_local, "fNL_equil": f_eq}
class InflationSRModel(BaseCosmoModel):
    """Slow-roll inflation families (monomial/plateau) with derived observables."""

    name = "inflation_slowroll"

    def compute_observables(self) -> Dict[str, float]:
        N = float(self.params.get("N", 55.0))
        pot = str(self.params.get("potential", "m2phi2")).lower()
        As = float(self.params.get("As", 2.1e-9))

        if pot in {"plateau", "starobinsky"}:
            base = _starobinsky_from_N(N)
        else:
            p = {"m2phi2": 2.0, "lambda_phi4": 4.0, "phi_p": float(self.params.get("p", 2.0))}.get(pot, 2.0)
            base = _sr_from_N(p, N)

        ns, r = base["ns"], base["r"]
        eps = r / 16.0
        # Amplitude fixes H_* (M_pl=1 units): As = H^2/(8π^2 ε)
        H = (8.0 * pi * pi * eps * As) ** 0.5 if eps > 0 else 0.0
        V = 3.0 * H * H

        obs = dict(base)
        obs.update(_single_field_fnl(ns, r))
        obs.update({"As": As, "H_star": H, "V_star": V, "eps": eps})
        return obs
class ReheatingProxyModel(BaseCosmoModel):
    """Reheating proxy: maps (w_re, T_re) + inflation amplitude into N_re etc."""

    name = "reheating_proxy"

    def compute_observables(self) -> Dict[str, float]:
        w = float(self.params.get("w_re", 0.0))
        T = float(self.params.get("T_re", 1e9))  # GeV-like scale proxy
        g = float(self.params.get("g_re", 100.0))
        infl = InflationSRModel(**{k: self.params.get(k) for k in ("N", "potential", "p", "As") if k in self.params}).compute_observables()
        rho_end = float(self.params.get("rho_end", infl["V_star"]))  # proxy
        rho_re = (pi * pi / 30.0) * g * (T ** 4)
        denom = 3.0 * (1.0 + w)
        N_re = (log(max(rho_end, 1e-300)) - log(max(rho_re, 1e-300))) / denom if denom != 0 else 0.0
        # Convert to a simple effective "reheating imprint" scale shift
        k_shift = exp(-N_re)

        return {"N_re": N_re, "a_re_over_a_end": exp(N_re), "k_reheat_shift": k_shift, "w_re": w, "T_re": T}
class TransPlanckianModulationModel(BaseCosmoModel):
    """Trans-Planckian-inspired oscillatory modulation parameters (proxy-level)."""

    name = "transplanckian_modulation"

    def compute_observables(self) -> Dict[str, float]:
        beta = float(self.params.get("beta", 0.01))  # modulation amplitude
        k_tp = float(self.params.get("k_tp", 0.05))  # 1/Mpc pivot-ish
        phase = float(self.params.get("phase", 0.0))
        k_pivot = float(self.params.get("k_pivot", 0.05))
        delta = beta * sin(2.0 * (k_pivot / max(k_tp, 1e-30)) + phase)
        return {"tp_beta": beta, "tp_k_tp": k_tp, "tp_phase": phase, "deltaP_over_P_pivot": delta}
class NonInflationEkpyroticProxyModel(BaseCosmoModel):
    """Ekpyrotic-like contraction proxy (tilt + local NG), not a full solver."""

    name = "ekpyrotic_proxy"

    def compute_observables(self) -> Dict[str, float]:
        # Parameterize by fast-roll ε_c >> 1; ns-1 ~ 2/ε_c in minimal setups (proxy).
        eps_c = float(self.params.get("eps_c", 50.0))
        ns = 1.0 + 2.0 / eps_c
        r = float(self.params.get("r", 0.0))  # typically negligible
        f_local = float(self.params.get("fNL_local", 10.0))  # often sizable/sign-changing
        return {"ns": ns, "r": r, "alpha_s": -2.0 / (eps_c * eps_c), "fNL_local": f_local, "eps_c": eps_c}
class DarkEnergyCPLModel(BaseCosmoModel):
    """Late-time dark energy with CPL equation of state w(a)=w0+wa(1-a)."""

    name = "dark_energy_cpl"

    def compute_observables(self) -> Dict[str, float]:
        w0 = float(self.params.get("w0", -1.0))
        wa = float(self.params.get("wa", 0.0))
        z_p = float(self.params.get("z_pivot", 0.5))
        a_p = 1.0 / (1.0 + z_p)
        w_p = w0 + wa * (1.0 - a_p)
        # Proxy growth index (Linder-like) around ΛCDM.
        gamma = 0.55 + 0.05 * (1.0 + w0 + 0.5 * wa)
        return {"w0": w0, "wa": wa, "w_pivot": w_p, "gamma_growth": gamma}
_REGISTRY = {
    InflationSRModel.name: InflationSRModel,
    ReheatingProxyModel.name: ReheatingProxyModel,
    TransPlanckianModulationModel.name: TransPlanckianModulationModel,
    NonInflationEkpyroticProxyModel.name: NonInflationEkpyroticProxyModel,
    DarkEnergyCPLModel.name: DarkEnergyCPLModel,
}

def create_model(name: str, **params: Any) -> BaseCosmoModel:
    """Factory for configured backends."""
    cls = _REGISTRY.get(name)
    if cls is None:
        raise KeyError(f"Unknown model '{name}'. Known: {sorted(_REGISTRY)}")
    return cls(**params)

def available_models() -> Mapping[str, Any]:
    return dict(_REGISTRY)
