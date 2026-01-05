"""Analysis-plan generator for psyprim.

Produces empirically grounded analysis plans for adoption-effect estimation:
statistical models, power/MDES heuristics, qualitative coding, and reporting templates.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from math import sqrt
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_ALPHA = 0.05
DEFAULT_POWER = 0.8


def _z_approx(p: float) -> float:
    """Fast normal-quantile approximation (Acklam-like, coarse but usable for MDES)."""
    if p <= 0 or p >= 1:
        raise ValueError("p must be in (0,1)")
    a = [ -3.969683028665376e+01,  2.209460984245205e+02, -2.759285104469687e+02,
          1.383577518672690e+02, -3.066479806614716e+01,  2.506628277459239e+00 ]
    b = [ -5.447609879822406e+01,  1.615858368580409e+02, -1.556989798598866e+02,
          6.680131188771972e+01, -1.328068155288572e+01 ]
    c = [ -7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
          -2.549732539343734e+00,  4.374664141464968e+00,  2.938163982698783e+00 ]
    d = [  7.784695709041462e-03,  3.224671290700398e-01,  2.445134137142996e+00,
           3.754408661907416e+00 ]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = sqrt(-2 * __import__("math").log(p))
        return (((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) /                ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1)
    if p > phigh:
        q = sqrt(-2 * __import__("math").log(1 - p))
        return -(((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) /                 ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1)
    q = p - 0.5
    r = q*q
    return (((((a[0]*r + a[1])*r + a[2])*r + a[3])*r + a[4])*r + a[5]) * q /            (((((b[0]*r + b[1])*r + b[2])*r + b[3])*r + b[4])*r + 1)


def mdes_two_sample_mean(sd: float, n_t: int, n_c: int, alpha: float = DEFAULT_ALPHA, power: float = DEFAULT_POWER) -> float:
    """Minimum detectable difference in means (absolute units), two-sided z approximation."""
    if sd <= 0 or n_t <= 1 or n_c <= 1:
        raise ValueError("sd>0 and n_t,n_c>1 required")
    z = _z_approx(1 - alpha/2) + _z_approx(power)
    se = sd * sqrt(1/n_t + 1/n_c)
    return z * se


def mdes_two_sample_smd(n_t: int, n_c: int, alpha: float = DEFAULT_ALPHA, power: float = DEFAULT_POWER) -> float:
    """MDES in standardized mean difference units (Cohen's d)."""
    z = _z_approx(1 - alpha/2) + _z_approx(power)
    return z * sqrt(1/n_t + 1/n_c)


def mdes_two_prop(p_pool: float, n_t: int, n_c: int, alpha: float = DEFAULT_ALPHA, power: float = DEFAULT_POWER) -> float:
    """MDES for difference in proportions using pooled variance at baseline p_pool."""
    if not (0 < p_pool < 1):
        raise ValueError("p_pool must be in (0,1)")
    z = _z_approx(1 - alpha/2) + _z_approx(power)
    se = sqrt(p_pool*(1-p_pool)*(1/n_t + 1/n_c))
    return z * se


def design_effect_cluster(m: float, icc: float) -> float:
    """Design effect for equal cluster sizes m and ICC."""
    if m <= 1:
        return 1.0
    if icc < 0:
        raise ValueError("icc must be >=0")
    return 1 + (m - 1) * icc


def effective_n(n: int, m: float, icc: float) -> float:
    """Effective sample size under clustering (approx)."""
    return n / design_effect_cluster(m, icc)


@dataclass
class AnalysisConfig:
    effect_family: str = "adoption_effect"
    study_design: str = "stepped_wedge_or_prepost"
    primary_outcomes: Tuple[str, ...] = ("citation_accuracy", "reproducibility", "usability")
    alpha: float = DEFAULT_ALPHA
    power: float = DEFAULT_POWER
    multiplicity: str = "BH_FDR"
    clustering_unit: Optional[str] = "lab_or_journal"
    missing_data: str = "MI_or_IPW_sensitivity"
    preregister: bool = True


def statistical_models() -> Dict[str, Any]:
    return {
        "audit_study_binary": {
            "estimand": "risk_difference_and_logit_OR",
            "model": "glm_binomial_with_cluster_robust_SE or mixed_logit",
            "formula": "y ~ tool_adoption + covariates + strata_fixed_effects",
            "notes": ["Use journal/field strata; cluster by lab or journal if relevant.", "Report RD, OR, and marginal effects."]
        },
        "audit_study_count": {
            "estimand": "rate_ratio",
            "model": "neg_binomial_or_poisson_quasi",
            "formula": "count ~ tool_adoption + offset(log(exposure)) + covariates",
            "notes": ["Use if outcome is #errors per article, exposure= #citations audited."]
        },
        "continuous_usability": {
            "estimand": "mean_difference_and_SMD",
            "model": "OLS_or_robust_regression; optionally mixed_effects",
            "formula": "score ~ tool_adoption + baseline_score + covariates",
            "notes": ["Use Huber-White SE; check ceiling effects."]
        },
        "did_panel": {
            "estimand": "ATT",
            "model": "difference_in_differences with unit and time fixed effects",
            "formula": "y_it ~ adopt_it + unit_FE + time_FE + time_varying_covariates",
            "notes": ["Event-study plots for pre-trends; cluster by unit."]
        },
        "stepped_wedge": {
            "estimand": "average_treatment_effect_over_time",
            "model": "GLMM with time fixed effects and cluster random intercepts",
            "formula": "y_ct ~ treated_ct + time_FE + (1|cluster)",
            "notes": ["Use Hussey-Hughes type approach; report ICC and sensitivity."]
        },
    }


def metrics_catalog() -> Dict[str, Any]:
    return {
        "citation_accuracy": {
            "operationalization": [
                "binary: any_primary_source_mismatch in audited set",
                "count: #mismatches per 20 randomly sampled citations",
                "severity-weighted error score (minor/major/critical)"
            ],
            "collection": "blinded double-audit with adjudication; compute inter-rater reliability (Krippendorff's alpha)."
        },
        "reproducibility": {
            "operationalization": [
                "binary: claim-verification success for extracted primary-source statements",
                "time-to-locate primary source and confirm claim",
                "replication packet completeness score"
            ],
            "collection": "task-based protocol; measure success rate, time, and completeness; log tool telemetry if consented."
        },
        "usability": {
            "operationalization": ["SUS score", "NASA-TLX", "completion time", "error rate in workflow tasks"],
            "collection": "within-subject task battery; counterbalanced order; capture qualitative think-aloud."
        },
        "adoption": {
            "operationalization": ["install/activation rate", "active use over 30/90 days", "workflow completion rate"],
            "collection": "opt-in telemetry + periodic surveys; triangulate with self-report."
        }
    }


def qualitative_coding_plan() -> Dict[str, Any]:
    return {
        "data_sources": ["semi-structured interviews", "open-ended survey responses", "issue tickets / forum posts (if consent)"],
        "approach": {
            "primary": "thematic_analysis_with_codebook",
            "secondary": "framework_analysis aligned to COM-B (capability, opportunity, motivation) and NPT (normalization process theory)"
        },
        "reliability": {
            "training": "two coders code 10-20% jointly; refine codebook",
            "double_code": ">=20% double-coded; compute Krippendorff's alpha; target >=0.67 exploratory, >=0.80 confirmatory",
            "disagreement": "adjudication with memoing; track code changes"
        },
        "outputs": ["barrier/facilitator map", "UX pain points tied to measurable workflow steps", "quotes for each theme with prevalence estimates"]
    }


def reporting_templates() -> Dict[str, str]:
    return {
        "primary_table": "Outcome | Estimand | Model | Effect (95% CI) | p | N | Clusters | ICC | Notes",
        "audit_appendix": "Sampling frame; citation-selection algorithm; auditor training; IRR; adjudication rules; error taxonomy.",
        "did_figures": "Event-study coefficients with 95% CI; pre-trend test; sensitivity to alternative windows/specifications.",
        "multiplicity": "List of outcomes/tests; adjustment method (BH FDR); report both adjusted and unadjusted p-values.",
        "reproducibility": "Provide anonymized protocol, code, and synthetic or de-identified data where feasible; document deviations."
    }


def build_analysis_plan(cfg: Optional[AnalysisConfig] = None, *, sample_sizes: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    cfg = cfg or AnalysisConfig()
    sample_sizes = sample_sizes or {"n_t": 200, "n_c": 200}
    n_t, n_c = sample_sizes.get("n_t", 200), sample_sizes.get("n_c", 200)
    mdes = {
        "SMD_two_sample": round(mdes_two_sample_smd(n_t, n_c, cfg.alpha, cfg.power), 4),
        "prop_diff_at_p=0.20": round(mdes_two_prop(0.20, n_t, n_c, cfg.alpha, cfg.power), 4),
        "prop_diff_at_p=0.50": round(mdes_two_prop(0.50, n_t, n_c, cfg.alpha, cfg.power), 4),
    }
    return {
        "config": asdict(cfg),
        "models": statistical_models(),
        "metrics": metrics_catalog(),
        "power_mdes_heuristics": {
            "notes": [
                "MDES uses z-approx; for final study run exact/simulation power (esp. mixed/cluster designs).",
                "For cluster designs, divide nominal N by design effect; report ICC and cluster sizes."
            ],
            "assumptions": {"alpha": cfg.alpha, "power": cfg.power, "n_t": n_t, "n_c": n_c},
            "mdes_examples": mdes,
            "cluster_adjustment": {"design_effect": "1+(m-1)*ICC", "effective_n": "N/design_effect"},
        },
        "qualitative": qualitative_coding_plan(),
        "reporting": reporting_templates(),
        "analysis_workflow": [
            "Pre-register estimands, outcomes, and exclusion criteria; publish audit protocol.",
            "Construct dataset with provenance: sampling frame -> sampled units -> audited citations/tasks -> outcomes.",
            "Fit primary model(s); compute robust/clustered SE; assess model fit; run sensitivity analyses.",
            "Multiplicity control (BH FDR) across primary outcomes; specify confirmatory vs exploratory.",
            "Triangulate quant results with qualitative themes; map barriers to measurable levers."
        ],
    }
