"""Heavy-tailed simulation utilities.

Provides data generators (Student-t and Pareto mixtures) plus helpers to run
repeated trials and return structured results suitable for saving/plotting.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Mapping, Optional, Sequence, Tuple, Union

import numpy as np


ArrayLike = Union[Sequence[float], np.ndarray]
Estimator = Callable[[np.ndarray, Optional[np.random.Generator]], float]
GeneratorFn = Callable[[int, Optional[np.random.Generator]], np.ndarray]
def _as_rng(rng: Optional[Union[int, np.random.Generator]]) -> np.random.Generator:
    if isinstance(rng, np.random.Generator):
        return rng
    return np.random.default_rng(None if rng is None else int(rng))


def student_t_generator(df: float = 2.5, loc: float = 0.0, scale: float = 1.0) -> GeneratorFn:
    """Return a generator that samples Student-t(df) with location/scale."""
    df = float(df)
    loc = float(loc)
    scale = float(scale)

    def gen(n: int, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        r = _as_rng(rng)
        x = r.standard_t(df, size=int(n))
        return loc + scale * x

    return gen


def pareto_mixture_generator(
    alpha: float = 1.5,
    p_heavy: float = 0.1,
    heavy_scale: float = 10.0,
    base_loc: float = 0.0,
    base_scale: float = 1.0,
) -> GeneratorFn:
    """Mixture: with prob (1-p_heavy) draw Normal, else symmetric Pareto tail.

    Heavy component magnitude: heavy_scale * (1 + Pareto(alpha)).
    Random sign makes it centered (mean may not exist if alpha<=1).
    """
    alpha = float(alpha)
    p_heavy = float(p_heavy)
    heavy_scale = float(heavy_scale)
    base_loc = float(base_loc)
    base_scale = float(base_scale)

    def gen(n: int, rng: Optional[np.random.Generator] = None) -> np.ndarray:
        r = _as_rng(rng)
        n = int(n)
        u = r.random(n)
        base = base_loc + base_scale * r.standard_normal(n)
        is_heavy = u < p_heavy
        k = int(is_heavy.sum())
        if k:
            mag = heavy_scale * (1.0 + r.pareto(alpha, size=k))
            sign = r.choice(np.array([-1.0, 1.0]), size=k)
            base[is_heavy] = sign * mag
        return base

    return gen
def estimate_truth(
    generator: GeneratorFn,
    *,
    rng: Optional[Union[int, np.random.Generator]] = 0,
    m: int = 200000,
    trim_quantile: float = 0.0,
) -> float:
    """Approximate E[X] (or a trimmed mean if trim_quantile>0) via Monte Carlo."""
    r = _as_rng(rng)
    x = generator(int(m), r)
    tq = float(trim_quantile)
    if tq <= 0:
        return float(np.mean(x))
    lo, hi = np.quantile(x, [tq, 1.0 - tq])
    y = x[(x >= lo) & (x <= hi)]
    return float(np.mean(y)) if y.size else float(np.mean(x))


def run_trials(
    *,
    generator: GeneratorFn,
    estimators: Mapping[str, Estimator],
    n: int,
    trials: int,
    truth: Optional[float] = None,
    truth_kwargs: Optional[Dict] = None,
    seed: Optional[int] = 0,
) -> Dict:
    """Run repeated trials, returning errors and summary statistics.

    Estimators are callables: est(x: np.ndarray, rng: Optional[Generator]) -> float
    (rng provided for estimators needing randomness; deterministic estimators ignore it).
    """
    n = int(n)
    trials = int(trials)
    if truth is None:
        truth_kwargs = truth_kwargs or {}
        truth = estimate_truth(generator, rng=seed, **truth_kwargs)

    base_rng = _as_rng(seed)
    names = list(estimators.keys())
    errors = {k: np.empty(trials, dtype=float) for k in names}

    for t in range(trials):
        r_data = np.random.default_rng(base_rng.integers(0, 2**63 - 1, dtype=np.int64))
        r_est = np.random.default_rng(base_rng.integers(0, 2**63 - 1, dtype=np.int64))
        x = generator(n, r_data)
        for name, est in estimators.items():
            val = float(est(x, r_est))
            errors[name][t] = val - float(truth)

    summary = {}
    for name in names:
        e = errors[name]
        ae = np.abs(e)
        summary[name] = {
            "bias": float(np.mean(e)),
            "rmse": float(np.sqrt(np.mean(e * e))),
            "mae": float(np.mean(ae)),
            "median_abs_error": float(np.median(ae)),
            "p90_abs_error": float(np.quantile(ae, 0.9)),
        }

    return {
        "n": n,
        "trials": trials,
        "truth": float(truth),
        "errors": {k: errors[k].tolist() for k in names},
        "summary": summary,
        "estimators": names,
    }
