"""Statistical pipeline utilities.

This module provides lightweight, dependency-minimal building blocks for
confronting swampland-constrained cosmology models with data:
- Likelihood composition (Gaussian & multivariate Gaussian)
- Priors and transforms (uniform/log-uniform/normal)
- Posterior evaluation + a small MCMC sampler (random-walk Metropolis)
- Simple evidence/model comparison surrogates (AIC/BIC + Laplace evidence)
- Forecast hooks (Fisher matrix via numerical derivatives)

The intent is to be backend-agnostic: a "model" is any callable mapping
a parameter dict -> observable dict or vector.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union
import math
import numpy as np

Array = np.ndarray
Params = Dict[str, float]


# ---------------------------- Likelihoods --------------------------------- #

@dataclass(frozen=True)
class Likelihood:
    """Base class: implement __call__(theta)->logL."""
    def __call__(self, theta: Params) -> float:  # pragma: no cover
        raise NotImplementedError


@dataclass(frozen=True)
class GaussianLikelihood(Likelihood):
    """Independent Gaussian likelihood for a set of named observables."""
    data: Mapping[str, float]
    sigma: Mapping[str, float]
    predict: Callable[[Params], Mapping[str, float]]

    def __call__(self, theta: Params) -> float:
        pred = self.predict(theta)
        ll = 0.0
        for k, y in self.data.items():
            s = float(self.sigma[k])
            r = (float(pred[k]) - float(y)) / s
            ll += -0.5 * (r * r + math.log(2 * math.pi * s * s))
        return float(ll)


@dataclass(frozen=True)
class MVGaussianLikelihood(Likelihood):
    """Multivariate Gaussian likelihood for a vector-valued observable."""
    y: Array
    cov: Array
    predict: Callable[[Params], Array]

    def __post_init__(self):
        ic = np.linalg.inv(self.cov)
        object.__setattr__(self, "_icov", ic)
        sign, logdet = np.linalg.slogdet(self.cov)
        if sign <= 0:
            raise ValueError("Covariance must be positive definite.")
        object.__setattr__(self, "_lognorm", 0.5 * (len(self.y) * math.log(2 * math.pi) + logdet))

    def __call__(self, theta: Params) -> float:
        r = np.asarray(self.predict(theta), dtype=float) - np.asarray(self.y, dtype=float)
        q = float(r.T @ self._icov @ r)
        return float(-0.5 * q - self._lognorm)


@dataclass(frozen=True)
class SumLikelihood(Likelihood):
    parts: Sequence[Likelihood]
    def __call__(self, theta: Params) -> float:
        return float(sum(p(theta) for p in self.parts))


# ------------------------------ Priors ------------------------------------ #

@dataclass(frozen=True)
class Prior:
    name: str
    def logpdf(self, x: float) -> float:  # pragma: no cover
        raise NotImplementedError
    def sample(self, rng: np.random.Generator) -> float:  # pragma: no cover
        raise NotImplementedError


@dataclass(frozen=True)
class UniformPrior(Prior):
    lo: float
    hi: float
    def logpdf(self, x: float) -> float:
        if self.lo <= x <= self.hi:
            return -math.log(self.hi - self.lo)
        return -math.inf
    def sample(self, rng: np.random.Generator) -> float:
        return float(rng.uniform(self.lo, self.hi))


@dataclass(frozen=True)
class LogUniformPrior(Prior):
    lo: float
    hi: float
    def __post_init__(self):
        if self.lo <= 0 or self.hi <= 0:
            raise ValueError("LogUniform bounds must be positive.")
    def logpdf(self, x: float) -> float:
        if self.lo <= x <= self.hi:
            return -math.log(x) - math.log(math.log(self.hi / self.lo))
        return -math.inf
    def sample(self, rng: np.random.Generator) -> float:
        u = rng.uniform(0.0, 1.0)
        return float(self.lo * (self.hi / self.lo) ** u)


@dataclass(frozen=True)
class NormalPrior(Prior):
    mu: float
    sigma: float
    def logpdf(self, x: float) -> float:
        z = (x - self.mu) / self.sigma
        return float(-0.5 * (z * z + math.log(2 * math.pi * self.sigma * self.sigma)))
    def sample(self, rng: np.random.Generator) -> float:
        return float(rng.normal(self.mu, self.sigma))


def log_prior(theta: Params, priors: Sequence[Prior]) -> float:
    lp = 0.0
    for p in priors:
        lp += p.logpdf(float(theta[p.name]))
        if not np.isfinite(lp):
            return -math.inf
    return float(lp)


def sample_from_priors(priors: Sequence[Prior], rng: Optional[np.random.Generator] = None) -> Params:
    rng = np.random.default_rng() if rng is None else rng
    return {p.name: p.sample(rng) for p in priors}


# ------------------------- Posterior + inference -------------------------- #

def log_posterior(theta: Params, like: Likelihood, priors: Sequence[Prior]) -> float:
    lp = log_prior(theta, priors)
    if not np.isfinite(lp):
        return -math.inf
    ll = like(theta)
    return float(lp + ll)


def metropolis_hastings(
    init: Params,
    like: Likelihood,
    priors: Sequence[Prior],
    step: Mapping[str, float],
    n: int,
    burn: int = 0,
    thin: int = 1,
    rng: Optional[np.random.Generator] = None,
) -> Tuple[List[Params], Array, float]:
    """Random-walk MH. Returns (samples, logpost, acceptance_rate)."""
    rng = np.random.default_rng() if rng is None else rng
    keys = list(init.keys())
    cur = dict(init)
    cur_lp = log_posterior(cur, like, priors)
    acc = 0
    out: List[Params] = []
    lps: List[float] = []
    for i in range(n):
        prop = dict(cur)
        for k in keys:
            prop[k] = float(prop[k] + rng.normal(0.0, float(step.get(k, 0.0))))
        prop_lp = log_posterior(prop, like, priors)
        if math.log(rng.uniform()) < (prop_lp - cur_lp):
            cur, cur_lp = prop, prop_lp
            acc += 1
        if i >= burn and ((i - burn) % thin == 0):
            out.append(dict(cur))
            lps.append(cur_lp)
    return out, np.asarray(lps, dtype=float), acc / max(1, n)


# ------------------------- Model comparison -------------------------------- #

def aic_bic(max_loglike: float, k: int, n_data: int) -> Tuple[float, float]:
    """AIC/BIC for quick ranking when evidence is unavailable."""
    aic = 2 * k - 2 * max_loglike
    bic = k * math.log(max(1, n_data)) - 2 * max_loglike
    return float(aic), float(bic)


def laplace_log_evidence(mle: Array, logpost: Callable[[Array], float], hess: Array) -> float:
    """Laplace approx to log evidence around MLE/MAP with Hessian of -logpost."""
    k = len(mle)
    sign, logdet = np.linalg.slogdet(hess)
    if sign <= 0:
        raise ValueError("Hessian must be positive definite for Laplace evidence.")
    return float(logpost(mle) + 0.5 * k * math.log(2 * math.pi) - 0.5 * logdet)


# ------------------------------ Forecasting -------------------------------- #

def fisher_matrix(
    theta0: Params,
    like_builder: Callable[[Params], Likelihood],
    params: Sequence[str],
    eps: Union[float, Mapping[str, float]] = 1e-3,
) -> Array:
    """Numerical Fisher matrix using second derivatives of -logL at theta0."""
    eps_map = {p: float(eps[p]) for p in params} if isinstance(eps, Mapping) else {p: float(eps) for p in params}
    base_like = like_builder(theta0)
    def nll(th: Params) -> float:
        return float(-base_like(th))
    k = len(params)
    F = np.zeros((k, k), dtype=float)
    for i, pi in enumerate(params):
        for j, pj in enumerate(params[i:], start=i):
            hi, hj = eps_map[pi], eps_map[pj]
            tpp = dict(theta0); tpp[pi] += hi; tpp[pj] += hj
            tpm = dict(theta0); tpm[pi] += hi; tpm[pj] -= hj
            tmp = dict(theta0); tmp[pi] -= hi; tmp[pj] += hj
            tmm = dict(theta0); tmm[pi] -= hi; tmm[pj] -= hj
            val = (nll(tpp) - nll(tpm) - nll(tmp) + nll(tmm)) / (4 * hi * hj)
            F[i, j] = F[j, i] = float(val)
    return F
