"""Causal-chain planning utilities for longitudinal multi-wave RCTs.

This module generates analysis-ready *specifications* (dicts) describing:
- mediation and moderation tests,
- estimands, identification assumptions, and
- model formulas for common longitudinal analyses.

Design goal: lightweight, schema-agnostic, easy to serialize to JSON/YAML.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union


Json = Dict[str, Any]


def _as_list(x: Union[str, Sequence[str], None]) -> List[str]:
    if x is None:
        return []
    if isinstance(x, str):
        return [x]
    return list(x)


def _join_terms(terms: Iterable[str]) -> str:
    t = [s.strip() for s in terms if s and s.strip()]
    return " + ".join(dict.fromkeys(t)) if t else "1"


def _interaction(a: str, b: str) -> str:
    return f"{a}:{b}"


def _lag(var: str, k: int) -> str:
    return f"lag{int(k)}({var})"


def default_assumptions(
    randomized: bool = True,
    longitudinal: bool = True,
    interference: str = "none",
    missingness: str = "MAR_given_observed",
) -> List[str]:
    base = [
        "Consistency (treatment versions well-defined; potential outcomes map to observed outcomes under realized treatment).",
        "Positivity (nonzero probability of each treatment level within covariate strata used for adjustment).",
        f"Interference: {interference} (SUTVA component; adjust design/analysis if clustering or spillovers).",
        f"Missingness: {missingness} (state handling; consider IPW/MI/sensitivity if violated).",
    ]
    if randomized:
        base.insert(0, "Randomization (ignorability of assigned treatment at each randomization point).")
    if longitudinal:
        base.append(
            "Sequential exchangeability for time-varying mediators/covariates after conditioning on specified history (for natural effects / g-methods)."
        )
    return base


@dataclass(frozen=True)
class ModelFormula:
    family: str
    formula: str
    notes: str = ""

    def to_json(self) -> Json:
        return {"family": self.family, "formula": self.formula, "notes": self.notes}


def make_mixed_formula(
    outcome: str,
    fixed: Sequence[str],
    group: str = "child_id",
    random_slope: Optional[str] = None,
    time: Optional[str] = "wave",
    add_time_fe: bool = True,
) -> ModelFormula:
    fx = list(fixed)
    if add_time_fe and time:
        fx.append(f"C({time})")
    rhs = _join_terms(fx)
    re = f"(1|{group})" if not random_slope else f"(1 + {random_slope}|{group})"
    return ModelFormula(family="gaussian_mixed", formula=f"{outcome} ~ {rhs} + {re}")


def make_glm_formula(outcome: str, fixed: Sequence[str], family: str = "binomial", time: Optional[str] = "wave") -> ModelFormula:
    fx = list(fixed)
    if time:
        fx.append(f"C({time})")
    return ModelFormula(family=family, formula=f"{outcome} ~ {_join_terms(fx)}")


def mediation_spec(
    *,
    name: str,
    treatment: str,
    mediator: str,
    outcome: str,
    waves: Sequence[int],
    baseline_covariates: Sequence[str] = (),
    time_varying_covariates: Sequence[str] = (),
    moderator: Optional[str] = None,
    effect_type: str = "natural_indirect_and_direct",
    estimator: str = "product_of_coefficients",
    id_col: str = "child_id",
    time_col: str = "wave",
) -> Json:
    """Create a longitudinal mediation test spec.

    Waves indicate when mediator/outcome are measured; the implied ordering is:
    treatment at wave t influences mediator at t (or t+1), which influences outcome at t+1.
    """
    base = _as_list(baseline_covariates)
    tv = _as_list(time_varying_covariates)
    w = list(waves)
    if len(w) < 2:
        raise ValueError("waves must include at least two measurement waves for mediation.")
    # Use a simple lag-1 structure by default.
    m_t = f"{mediator}"
    y_tp1 = f"{outcome}"
    a = treatment

    m_fixed = [a] + base + [f"{c}" for c in tv] + [f"C({time_col})"]
    y_fixed = [a, m_t] + base + [f"{c}" for c in tv] + [f"C({time_col})"]

    if moderator:
        m_fixed += [_interaction(a, moderator)]
        y_fixed += [_interaction(a, moderator), _interaction(m_t, moderator)]

    spec = {
        "type": "mediation",
        "name": name,
        "effect_type": effect_type,
        "estimator": estimator,
        "variables": {
            "treatment": a,
            "mediator": mediator,
            "outcome": outcome,
            "moderator": moderator,
            "id_col": id_col,
            "time_col": time_col,
            "waves": w,
        },
        "estimands": {
            "total_effect": f"E[{y_tp1}|do({a}=1)] - E[{y_tp1}|do({a}=0)]",
            "natural_indirect_effect": f"E[Y({a}=1, M({a}=1))] - E[Y({a}=1, M({a}=0))]",
            "natural_direct_effect": f"E[Y({a}=1, M({a}=0))] - E[Y({a}=0, M({a}=0))]",
        },
        "identification_assumptions": default_assumptions(randomized=True, longitudinal=True),
        "models": {
            "mediator_model": make_mixed_formula(mediator, m_fixed, group=id_col, time=time_col).to_json(),
            "outcome_model": make_mixed_formula(outcome, y_fixed, group=id_col, time=time_col).to_json(),
        },
        "notes": [
            "Default specification assumes a lag-1 causal ordering; adjust by providing lagged variables in time_varying_covariates if needed.",
            "For binary/non-Gaussian mediators/outcomes, swap models to GLM/GEE and use appropriate causal mediation estimator.",
        ],
    }
    return spec


def moderation_spec(
    *,
    name: str,
    treatment: str,
    outcome: str,
    moderator: str,
    waves: Sequence[int],
    baseline_covariates: Sequence[str] = (),
    time_varying_covariates: Sequence[str] = (),
    id_col: str = "child_id",
    time_col: str = "wave",
    family: str = "gaussian_mixed",
) -> Json:
    base = _as_list(baseline_covariates)
    tv = _as_list(time_varying_covariates)
    a = treatment
    z = moderator
    y = outcome
    fixed = [a, z, _interaction(a, z)] + base + tv + [f"C({time_col})"]
    model = make_mixed_formula(y, fixed, group=id_col, time=time_col) if family == "gaussian_mixed" else make_glm_formula(y, fixed, family=family, time=time_col)
    return {
        "type": "moderation",
        "name": name,
        "variables": {"treatment": a, "outcome": y, "moderator": z, "id_col": id_col, "time_col": time_col, "waves": list(waves)},
        "estimands": {"interaction_effect": f"d/d{a} E[{y}|{a},{z}] varies with {z}; test coefficient on {a}:{z}"},
        "identification_assumptions": default_assumptions(randomized=True, longitudinal=False),
        "models": {"outcome_model": model.to_json()},
    }


def chain_spec(
    *,
    name: str,
    nodes: Sequence[str],
    edges: Sequence[Tuple[str, str]],
    tests: Sequence[Json],
    primary_estimand: str = "ATE",
    assumptions: Optional[Sequence[str]] = None,
) -> Json:
    """Bundle a causal chain diagram + planned tests into a single spec."""
    nd = list(nodes)
    ed = [{"from": a, "to": b} for a, b in edges]
    return {
        "type": "causal_chain",
        "name": name,
        "primary_estimand": primary_estimand,
        "nodes": nd,
        "edges": ed,
        "tests": list(tests),
        "identification_assumptions": list(assumptions) if assumptions is not None else default_assumptions(),
    }


def pretty_formula(spec: Mapping[str, Any]) -> List[str]:
    """Extract human-readable formulas from a mediation/moderation spec."""
    out: List[str] = []
    models = spec.get("models", {}) if isinstance(spec, Mapping) else {}
    for k, v in models.items():
        if isinstance(v, Mapping) and "formula" in v:
            out.append(f"{k}: {v.get('formula')}")
    return out
