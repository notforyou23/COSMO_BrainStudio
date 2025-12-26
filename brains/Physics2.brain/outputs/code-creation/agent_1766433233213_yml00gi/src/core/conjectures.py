"""Swampland conjecture encodings.

This module provides compact, model-agnostic objects used by the rest of the
package to translate theory constraints into bounds/priors over cosmological
model parameters and derived quantities.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Tuple

import math
import numpy as np
# ----------------------------- Priors ---------------------------------


@dataclass(frozen=True)
class Prior:
    """Lightweight prior object.

    Parameters
    ----------
    kind: {'uniform','loguniform','normal','delta'}
    params: distribution parameters (see `logpdf`).
    """

    kind: str
    params: Tuple[float, ...]
    name: str = ""

    def sample(self, rng: np.random.Generator) -> float:
        k, p = self.kind, self.params
        if k == "uniform":
            lo, hi = p
            return float(rng.uniform(lo, hi))
        if k == "loguniform":
            lo, hi = p
            return float(math.exp(rng.uniform(math.log(lo), math.log(hi))))
        if k == "normal":
            mu, sig = p
            return float(rng.normal(mu, sig))
        if k == "delta":
            (x,) = p
            return float(x)
        raise ValueError(f"Unknown prior kind: {k}")

    def logpdf(self, x: float) -> float:
        k, p = self.kind, self.params
        if k == "uniform":
            lo, hi = p
            return -math.log(hi - lo) if (lo <= x <= hi) else -math.inf
        if k == "loguniform":
            lo, hi = p
            if not (lo <= x <= hi) or x <= 0:
                return -math.inf
            return -math.log(x) - math.log(math.log(hi / lo))
        if k == "normal":
            mu, sig = p
            return -0.5 * ((x - mu) / sig) ** 2 - math.log(sig * math.sqrt(2 * math.pi))
        if k == "delta":
            (x0,) = p
            return 0.0 if x == x0 else -math.inf
        raise ValueError(f"Unknown prior kind: {k}")
# --------------------------- Conjectures -------------------------------


@dataclass(frozen=True)
class EvalResult:
    ok: bool
    metric: float
    threshold: float
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def violation(self) -> float:
        """Positive means a violation amount, 0 means satisfied."""
        return float(max(0.0, self.threshold - self.metric))


Evaluator = Callable[[Mapping[str, Any], Mapping[str, float]], EvalResult]


@dataclass(frozen=True)
class Conjecture:
    """A named conjecture with parameters + an evaluator.

    `params` are the conjecture's free constants (e.g. c, c').
    `priors` are optional priors over those constants for sampling/forecasting.
    """

    name: str
    params: Tuple[str, ...]
    evaluator: Evaluator
    priors: Dict[str, Prior] = field(default_factory=dict)
    reference: str = ""

    def sample_params(self, rng: np.random.Generator) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for k in self.params:
            pr = self.priors.get(k)
            if pr is None:
                raise KeyError(f"Missing prior for parameter '{k}' in {self.name}")
            out[k] = pr.sample(rng)
        return out

    def evaluate(self, model: Mapping[str, Any], params: Mapping[str, float]) -> EvalResult:
        return self.evaluator(model, params)
# ---------------------- Built-in evaluators ----------------------------


def _req(model: Mapping[str, Any], *keys: str) -> None:
    missing = [k for k in keys if k not in model]
    if missing:
        raise KeyError(f"Model missing required quantities: {missing}")


def eval_ds_slope(model: Mapping[str, Any], p: Mapping[str, float]) -> EvalResult:
    """De Sitter slope conjecture: |∇V|/V >= c (in reduced Planck units)."""
    _req(model, "V", "dV_dphi")
    V = float(model["V"])
    grad = float(model["dV_dphi"])
    c = float(p["c"])
    metric = abs(grad) / max(abs(V), 1e-300)
    ok = metric >= c
    return EvalResult(ok=ok, metric=metric, threshold=c, details={"V": V, "dV_dphi": grad})


def eval_refined_ds(model: Mapping[str, Any], p: Mapping[str, float]) -> EvalResult:
    """Refined de Sitter: either slope bound OR tachyon bound holds.

    Uses model quantities:
      - 'V', 'dV_dphi' for slope, and
      - 'hess_min' for the minimum Hessian eigenvalue of V in field space.
    Condition: (|∇V|/V >= c) OR (hess_min/V <= -c').
    """
    _req(model, "V", "dV_dphi", "hess_min")
    V = float(model["V"])
    grad = float(model["dV_dphi"])
    lam_min = float(model["hess_min"])
    c = float(p["c"])
    cp = float(p["cp"])
    slope = abs(grad) / max(abs(V), 1e-300)
    eta = lam_min / max(abs(V), 1e-300)
    ok = (slope >= c) or (eta <= -cp)
    # return metric as max satisfaction margin for simple scoring
    metric = max(slope / max(c, 1e-300), (-eta) / max(cp, 1e-300))
    return EvalResult(ok=ok, metric=metric, threshold=1.0, details={"slope": slope, "etaV": eta})


def eval_distance(model: Mapping[str, Any], p: Mapping[str, float]) -> EvalResult:
    """Distance conjecture: Δφ <= d (field excursion in Planck units)."""
    _req(model, "delta_phi")
    dphi = float(model["delta_phi"])
    d = float(p["d"])
    ok = dphi <= d
    # metric: remaining headroom (>=0 is ok)
    metric = d - dphi
    return EvalResult(ok=ok, metric=metric, threshold=0.0, details={"delta_phi": dphi, "d": d})


def eval_wgc_axion(model: Mapping[str, Any], p: Mapping[str, float]) -> EvalResult:
    """Simple axionic WGC proxy: f <= 1/kappa.

    Requires model quantity 'f_axion' (decay constant in Mpl units).
    Parameter kappa is O(1) and encodes instanton action/model dependence.
    """
    _req(model, "f_axion")
    f = float(model["f_axion"])
    kappa = float(p["kappa"])
    thr = 1.0 / max(kappa, 1e-300)
    ok = f <= thr
    metric = thr - f
    return EvalResult(ok=ok, metric=metric, threshold=0.0, details={"f_axion": f, "f_max": thr})
# --------------------- Factory / registry ------------------------------


def default_conjectures() -> Dict[str, Conjecture]:
    """Return a small, opinionated registry of standard conjectures."""
    return {
        "ds_slope": Conjecture(
            name="DeSitterSlope",
            params=("c",),
            evaluator=eval_ds_slope,
            priors={"c": Prior("loguniform", (1e-3, 1.0), name="c")},
            reference="Obied et al. (2018); Ooguri et al. (2019)",
        ),
        "refined_ds": Conjecture(
            name="RefinedDeSitter",
            params=("c", "cp"),
            evaluator=eval_refined_ds,
            priors={
                "c": Prior("loguniform", (1e-3, 1.0), name="c"),
                "cp": Prior("loguniform", (1e-3, 1.0), name="c'"),
            },
            reference="Garg & Krishnan (2018); Ooguri et al. (2019)",
        ),
        "distance": Conjecture(
            name="Distance",
            params=("d",),
            evaluator=eval_distance,
            priors={"d": Prior("uniform", (0.5, 10.0), name="d")},
            reference="Ooguri & Vafa (2006)",
        ),
        "wgc_axion": Conjecture(
            name="AxionWGCProxy",
            params=("kappa",),
            evaluator=eval_wgc_axion,
            priors={"kappa": Prior("loguniform", (0.1, 10.0), name="kappa")},
            reference="Weak Gravity Conjecture (axion proxy)",
        ),
    }


def evaluate_all(
    conjectures: Mapping[str, Conjecture],
    model: Mapping[str, Any],
    params: Mapping[str, Mapping[str, float]],
) -> Dict[str, EvalResult]:
    """Evaluate multiple conjectures against a model state."""
    out: Dict[str, EvalResult] = {}
    for key, conj in conjectures.items():
        out[key] = conj.evaluate(model, params.get(key, {}))
    return out
