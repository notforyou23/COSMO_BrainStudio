"""Robustness utilities for hypothesis stability under compactification/flux uncertainty.

This module provides:
- Scenario sampling (realistic compactification/flux choices via user-specified priors)
- Local sensitivity analysis (finite-difference gradients)
- Stress tests (tail scenarios and correlation shocks)

The module is deliberately backend-agnostic: users pass callables that map a scenario
(dict-like parameters) to hypothesis evaluation results.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np


Scenario = Dict[str, float]
EvalResult = Dict[str, Any]
EvaluateFn = Callable[[Scenario], EvalResult]
@dataclass(frozen=True)
class ScenarioSampler:
    """Sampler for compactification/flux scenarios.

    Parameters
    ----------
    base : baseline parameter point
    priors : mapping param -> callable(rng) -> float, or (low, high) for uniform
    corr : optional correlation matrix for a subset of keys (Gaussian copula).
           Provide as (keys, matrix) where matrix is positive semidefinite.
    """

    base: Scenario
    priors: Mapping[str, Any]
    corr: Optional[Tuple[Sequence[str], np.ndarray]] = None

    def _draw_one(self, rng: np.random.Generator) -> Scenario:
        s = dict(self.base)
        for k, prior in self.priors.items():
            if callable(prior):
                s[k] = float(prior(rng))
            else:
                lo, hi = prior
                s[k] = float(rng.uniform(lo, hi))
        if self.corr is not None:
            keys, mat = self.corr
            z = rng.multivariate_normal(np.zeros(len(keys)), mat)
            u = 0.5 * (1.0 + np.erf(z / np.sqrt(2.0)))  # normal CDF
            for i, k in enumerate(keys):
                prior = self.priors[k]
                if callable(prior):
                    # use inverse-CDF fallback: map u -> quantile via a small search
                    s[k] = float(_quantile_from_sampler(prior, u[i], rng))
                else:
                    lo, hi = prior
                    s[k] = float(lo + (hi - lo) * u[i])
        return s

    def sample(self, n: int, seed: Optional[int] = None) -> List[Scenario]:
        rng = np.random.default_rng(seed)
        return [self._draw_one(rng) for _ in range(int(n))]
def _quantile_from_sampler(prior: Callable[[np.random.Generator], float], q: float,
                           rng: np.random.Generator, m: int = 2048) -> float:
    """Approximate inverse-CDF for an arbitrary sampler prior using Monte Carlo."""
    xs = np.array([prior(rng) for _ in range(m)], dtype=float)
    xs.sort()
    idx = int(np.clip(q, 0.0, 1.0) * (m - 1))
    return float(xs[idx])


def evaluate_scenarios(evaluate: EvaluateFn, scenarios: Iterable[Scenario]) -> List[EvalResult]:
    """Evaluate a hypothesis/model function on many scenarios."""
    return [evaluate(dict(s)) for s in scenarios]
def stability_metrics(results: Sequence[EvalResult],
                      pass_key: str = "pass",
                      signature_key: str = "signature") -> Dict[str, Any]:
    """Summarize stability across scenarios.

    Expected EvalResult fields:
      - pass_key: bool, conjecture+consistency satisfied
      - signature_key: scalar (or array-like) observable signature value(s)
    """
    if not results:
        return {"n": 0, "pass_rate": np.nan, "signature_mean": None, "signature_std": None}

    passes = np.array([bool(r.get(pass_key, False)) for r in results])
    sigs = [r.get(signature_key, np.nan) for r in results]
    sigs = np.array(sigs, dtype=float) if np.isscalar(sigs[0]) else np.array(sigs, dtype=float)

    out: Dict[str, Any] = {"n": len(results), "pass_rate": float(passes.mean())}
    out["signature_mean"] = np.nanmean(sigs, axis=0).tolist() if sigs.ndim > 0 else float(np.nanmean(sigs))
    out["signature_std"] = np.nanstd(sigs, axis=0).tolist() if sigs.ndim > 0 else float(np.nanstd(sigs))
    return out
def finite_diff_sensitivity(evaluate: EvaluateFn,
                            scenario: Scenario,
                            keys: Sequence[str],
                            rel_step: float = 1e-2,
                            signature_key: str = "signature") -> Dict[str, float]:
    """Central finite-difference sensitivity of the signature wrt selected parameters."""
    base = dict(scenario)
    y0 = evaluate(base).get(signature_key, np.nan)
    if not np.isscalar(y0):
        y0 = float(np.asarray(y0).ravel()[0])

    sens: Dict[str, float] = {}
    for k in keys:
        x = float(base.get(k, 0.0))
        h = rel_step * (abs(x) + 1.0)
        up, dn = dict(base), dict(base)
        up[k], dn[k] = x + h, x - h
        yu = evaluate(up).get(signature_key, np.nan)
        yd = evaluate(dn).get(signature_key, np.nan)
        yu = float(np.asarray(yu).ravel()[0]) if not np.isscalar(yu) else float(yu)
        yd = float(np.asarray(yd).ravel()[0]) if not np.isscalar(yd) else float(yd)
        sens[k] = float((yu - yd) / (2.0 * h))
    sens["_baseline_signature"] = float(y0)
    return sens
def stress_test_tail_scenarios(sampler: ScenarioSampler,
                               evaluate: EvaluateFn,
                               n: int = 256,
                               tail_q: float = 0.98,
                               seed: Optional[int] = None,
                               signature_key: str = "signature") -> Dict[str, Any]:
    """Stress test using tail draws: keep scenarios with extreme signatures."""
    rng = np.random.default_rng(seed)
    scenarios = sampler.sample(int(n), seed=int(rng.integers(0, 2**32 - 1)))
    results = evaluate_scenarios(evaluate, scenarios)
    sig = np.array([r.get(signature_key, np.nan) for r in results], dtype=float)
    hi = np.nanquantile(sig, tail_q)
    lo = np.nanquantile(sig, 1.0 - tail_q)
    idx = np.where((sig >= hi) | (sig <= lo))[0]
    tail_results = [results[i] for i in idx.tolist()]
    return {"n_total": len(results), "n_tail": len(tail_results), "tail_metrics": stability_metrics(tail_results)}
def stress_test_correlation_shock(sampler: ScenarioSampler,
                                  evaluate: EvaluateFn,
                                  shock: float = 0.2,
                                  n: int = 512,
                                  seed: Optional[int] = None) -> Dict[str, Any]:
    """Stress test by perturbing the sampler's correlation matrix (if present)."""
    if sampler.corr is None:
        res = evaluate_scenarios(evaluate, sampler.sample(n, seed=seed))
        return {"applied": False, "metrics": stability_metrics(res)}

    keys, mat = sampler.corr
    rng = np.random.default_rng(seed)
    noise = rng.normal(scale=shock, size=mat.shape)
    mat2 = mat + 0.5 * (noise + noise.T)
    # project to PSD by clipping eigenvalues
    w, v = np.linalg.eigh(mat2)
    w = np.clip(w, 1e-8, None)
    mat2 = (v * w) @ v.T
    s2 = ScenarioSampler(base=sampler.base, priors=sampler.priors, corr=(list(keys), mat2))
    res = evaluate_scenarios(evaluate, s2.sample(n, seed=int(rng.integers(0, 2**32 - 1))))
    return {"applied": True, "shock": float(shock), "metrics": stability_metrics(res)}
def run_robustness_plan(evaluate: EvaluateFn,
                        sampler: ScenarioSampler,
                        n: int = 2048,
                        sensitivity_keys: Optional[Sequence[str]] = None,
                        seed: Optional[int] = None) -> Dict[str, Any]:
    """End-to-end robustness plan: sampling, metrics, sensitivity, stress tests."""
    scenarios = sampler.sample(int(n), seed=seed)
    results = evaluate_scenarios(evaluate, scenarios)
    report: Dict[str, Any] = {"metrics": stability_metrics(results), "n": int(n)}

    if sensitivity_keys:
        report["sensitivity"] = finite_diff_sensitivity(evaluate, sampler.base, list(sensitivity_keys))

    report["stress_tail"] = stress_test_tail_scenarios(sampler, evaluate, n=max(128, n // 8), seed=seed)
    report["stress_corr"] = stress_test_correlation_shock(sampler, evaluate, n=max(256, n // 4), seed=seed)
    return report
