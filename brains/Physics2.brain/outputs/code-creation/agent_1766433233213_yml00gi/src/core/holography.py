"""Holographic/entropy/quantum-information-inspired constraints.

This module provides lightweight, model-agnostic evaluators that map
holography-motivated bounds (dS entropy/Bousso, species, quantum break time)
to concrete cosmological parameter constraints and observable-level signatures
(e.g. upper bounds on H, r, maximal efolds).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Tuple
import math
_REDUCED_MPL_GEV = 2.435e18  # for optional GeV conversions; set mpl=1 for dimensionless work


def _get(x: Mapping[str, Any], key: str, default: Optional[float] = None) -> Optional[float]:
    v = x.get(key, default)
    return None if v is None else float(v)


def de_sitter_entropy(H: float, mpl: float = 1.0) -> float:
    """Gibbons-Hawking entropy S_dS = pi * (M_pl/H)^2 (reduced Planck mass)."""
    if H <= 0 or mpl <= 0:
        raise ValueError("H and mpl must be positive")
    return math.pi * (mpl / H) ** 2


def tensor_to_scalar_ratio(epsilon: float, c_s: float = 1.0) -> float:
    """Single-clock EFT relation r ≈ 16 ε c_s (used as a mapping, not a theorem)."""
    return max(0.0, 16.0 * float(epsilon) * float(c_s))
@dataclass(frozen=True)
class ConstraintResult:
    name: str
    passed: bool
    bounds: Dict[str, Tuple[Optional[float], Optional[float]]]
    implied: Dict[str, float]
    details: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "bounds": {k: {"min": v[0], "max": v[1]} for k, v in self.bounds.items()},
            "implied": dict(self.implied),
            "details": self.details,
        }


class HolographicConstraint:
    """Base class for holography-inspired constraints."""

    name: str = "base"

    def evaluate(self, params: Mapping[str, Any]) -> ConstraintResult:  # pragma: no cover
        raise NotImplementedError
@dataclass(frozen=True)
class DeSitterEntropyBound(HolographicConstraint):
    """dS entropy implies an absolute upper bound on the number of accessible states.

    Operational mapping: for a quasi-dS phase with H ~ const, require that
    the number of produced Hubble patches does not exceed S_dS:
        N <= (1/2) ln(S_dS)  (order-one mapping used in the literature as a testable prior)
    """

    name: str = "ds_entropy"
    factor: float = 0.5  # N_max = factor * ln(S_dS)
    mpl: float = 1.0

    def evaluate(self, params: Mapping[str, Any]) -> ConstraintResult:
        H = _get(params, "H")
        N = _get(params, "N")
        if H is None or N is None:
            return ConstraintResult(self.name, True, {}, {}, "missing H or N; not evaluated")
        S = de_sitter_entropy(H, self.mpl)
        N_max = self.factor * math.log(S)
        passed = N <= N_max + 1e-12
        bounds = {"N": (None, N_max), "H": (None, H)}
        implied = {"S_dS": S, "N_max": N_max}
        details = f"S_dS={S:.3e}, implied N_max={N_max:.3f} (mapping factor={self.factor})"
        return ConstraintResult(self.name, passed, bounds, implied, details)
@dataclass(frozen=True)
class SpeciesBound(HolographicConstraint):
    """Species bound: cutoff Λ ~ M_pl/sqrt(N_s), implying H < Λ for EFT validity."""

    name: str = "species"
    mpl: float = 1.0

    def evaluate(self, params: Mapping[str, Any]) -> ConstraintResult:
        H = _get(params, "H")
        Ns = _get(params, "N_species", 1.0)
        if H is None:
            return ConstraintResult(self.name, True, {}, {}, "missing H; not evaluated")
        Ns = max(1.0, float(Ns))
        Lambda = self.mpl / math.sqrt(Ns)
        passed = H < Lambda + 1e-12
        bounds = {"H": (None, Lambda)}
        implied = {"Lambda_species": Lambda}
        details = f"N_species={Ns:.3g}, Lambda={Lambda:.3g} (units of mpl)"
        return ConstraintResult(self.name, passed, bounds, implied, details)
@dataclass(frozen=True)
class QuantumBreakTime(HolographicConstraint):
    """Quantum break-time bound for (quasi-)dS.

    Use estimate t_q ~ M_pl^2 / (N_eff H^3). Requiring N/H < t_q gives:
        N < (M_pl/H)^2 / N_eff
    This maps to an upper bound on N at fixed H and N_eff.
    """

    name: str = "quantum_break"
    mpl: float = 1.0

    def evaluate(self, params: Mapping[str, Any]) -> ConstraintResult:
        H = _get(params, "H")
        N = _get(params, "N")
        Neff = _get(params, "N_eff", 1.0)
        if H is None or N is None:
            return ConstraintResult(self.name, True, {}, {}, "missing H or N; not evaluated")
        Neff = max(1.0, float(Neff))
        N_max = (self.mpl / H) ** 2 / Neff
        passed = N <= N_max + 1e-12
        bounds = {"N": (None, N_max)}
        implied = {"N_max": N_max, "N_eff": Neff}
        details = f"N_eff={Neff:.3g}, implied N_max={N_max:.3g}"
        return ConstraintResult(self.name, passed, bounds, implied, details)
def implied_observable_bounds(params: Mapping[str, Any]) -> Dict[str, float]:
    """Derive observable-level bounds implied by basic holographic inputs.

    Expected inputs: H (in mpl units), epsilon, c_s, A_s (scalar amplitude).
    Returns: r (from epsilon), r_from_H (if A_s given), and H_GeV if mpl provided.
    """
    out: Dict[str, float] = {}
    H = _get(params, "H")
    eps = _get(params, "epsilon")
    c_s = _get(params, "c_s", 1.0) or 1.0
    A_s = _get(params, "A_s")  # ~2.1e-9 from Planck; optional
    mpl = float(params.get("mpl", 1.0))

    if eps is not None:
        out["r"] = tensor_to_scalar_ratio(eps, c_s)
    if H is not None and A_s is not None and eps is not None and eps > 0:
        # A_s ≈ H^2/(8π^2 ε M_pl^2) => H ≈ 2√2 π M_pl √(A_s ε)
        out["H_from_As_eps"] = 2.0 * math.sqrt(2.0) * math.pi * mpl * math.sqrt(A_s * eps)
    if H is not None and mpl != 1.0:
        out["H_GeV"] = H * mpl * _REDUCED_MPL_GEV
    return out
def evaluate_holography(
    params: Mapping[str, Any],
    *,
    mpl: float = 1.0,
    include: Tuple[str, ...] = ("ds_entropy", "species", "quantum_break"),
) -> Dict[str, Any]:
    """Run a small suite of holographic constraints and return a compact report.

    params is a flat mapping produced by model backends, e.g.
      {H, N, epsilon, c_s, A_s, N_species, N_eff, mpl}
    """
    suite = {
        "ds_entropy": DeSitterEntropyBound(mpl=mpl),
        "species": SpeciesBound(mpl=mpl),
        "quantum_break": QuantumBreakTime(mpl=mpl),
    }
    results = [suite[k].evaluate(dict(params, mpl=mpl)) for k in include if k in suite]
    passed_all = all(r.passed for r in results)
    bounds: Dict[str, Tuple[Optional[float], Optional[float]]] = {}
    for r in results:
        for k, (mn, mx) in r.bounds.items():
            cur = bounds.get(k, (None, None))
            bounds[k] = (mn if cur[0] is None else max(cur[0], mn) if mn is not None else cur[0],
                         mx if cur[1] is None else min(cur[1], mx) if mx is not None else cur[1])
    report = {
        "passed": passed_all,
        "bounds": {k: {"min": v[0], "max": v[1]} for k, v in bounds.items()},
        "implied": implied_observable_bounds(dict(params, mpl=mpl)),
        "results": [r.to_dict() for r in results],
    }
    return report
