"""dgpipe.inference

Lightweight statistical inference utilities to translate measured correlator /
entanglement data into constraints on discrete-structure parameters.

Design goals: minimal dependencies (numpy only), support for Gaussian
likelihoods, additive linear systematics with analytic marginalization, and a
basic Metropolis-Hastings posterior sampler.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Mapping, Optional, Sequence, Tuple, Union

import numpy as np

Array = np.ndarray
PriorSpec = Union[Tuple[str, float, float], Tuple[str, Array, Array]]  # uniform/gaussian
def _as_1d(x: Union[Array, Sequence[float]]) -> Array:
    x = np.asarray(x, dtype=float)
    return x.reshape(-1)


def _cov_from_sigma(sigma: Union[float, Array], n: int) -> Array:
    s = np.asarray(sigma, dtype=float)
    if s.ndim == 0:
        return np.eye(n) * float(s) ** 2
    s = s.reshape(-1)
    if s.size != n:
        raise ValueError(f"sigma has size {s.size}, expected {n}")
    return np.diag(s ** 2)


def _loglike_gaussian(resid: Array, cov: Array) -> float:
    cov = np.asarray(cov, dtype=float)
    n = resid.size
    try:
        L = np.linalg.cholesky(cov)
        sol = np.linalg.solve(L, resid)
        quad = float(sol @ sol)
        logdet = 2.0 * float(np.log(np.diag(L)).sum())
    except np.linalg.LinAlgError:
        covi = np.linalg.pinv(cov)
        quad = float(resid @ covi @ resid)
        sign, logdet = np.linalg.slogdet(cov + 1e-12 * np.eye(n))
        logdet = float(logdet) if sign > 0 else float(np.log(np.abs(np.linalg.det(cov) + 1e-30)))
    return -0.5 * (quad + logdet + n * np.log(2.0 * np.pi))
def marginal_loglike_additive_linear(
    y: Array,
    mu: Array,
    cov_y: Array,
    A: Optional[Array] = None,
    nu_mean: Optional[Array] = None,
    nu_cov: Optional[Array] = None,
) -> float:
    """Gaussian log-likelihood with analytic marginalization over nuisance.

    Model: y = mu(theta) + A nu + eps,  eps~N(0,cov_y),  nu~N(nu_mean,nu_cov).
    The marginalized distribution is Gaussian with mean mu + A nu_mean and
    covariance cov_y + A nu_cov A^T.
    """
    y = _as_1d(y)
    mu = _as_1d(mu)
    if y.size != mu.size:
        raise ValueError("y and mu must have same length")
    cov_eff = np.asarray(cov_y, dtype=float)
    mean_eff = mu
    if A is not None and nu_cov is not None:
        A = np.asarray(A, dtype=float)
        nu_mean = np.zeros(A.shape[1]) if nu_mean is None else _as_1d(nu_mean)
        nu_cov = np.asarray(nu_cov, dtype=float)
        mean_eff = mu + A @ nu_mean
        cov_eff = cov_eff + A @ nu_cov @ A.T
    return _loglike_gaussian(y - mean_eff, cov_eff)
def logprior(theta: Array, priors: Optional[Mapping[str, PriorSpec]] = None, names: Optional[Sequence[str]] = None) -> float:
    """Compute log prior for parameter vector theta.

    priors maps parameter name -> ('uniform', low, high) or ('gaussian', mean, cov).
    For gaussian: mean and cov can be scalars (interpreted as diagonal variance) or arrays.
    """
    if not priors:
        return 0.0
    theta = _as_1d(theta)
    if names is None:
        names = [f"p{i}" for i in range(theta.size)]
    lp = 0.0
    for i, nm in enumerate(names):
        if nm not in priors:
            continue
        spec = priors[nm]
        if spec[0] == "uniform":
            lo, hi = float(spec[1]), float(spec[2])
            if not (lo <= theta[i] <= hi):
                return -np.inf
        elif spec[0] == "gaussian":
            mean = np.asarray(spec[1], dtype=float)
            cov = np.asarray(spec[2], dtype=float)
            m = float(mean) if mean.ndim == 0 else float(mean.reshape(-1)[0])
            v = float(cov) if cov.ndim == 0 else float(np.diag(cov).reshape(-1)[0])
            lp += -0.5 * ((theta[i] - m) ** 2 / v + np.log(2.0 * np.pi * v))
        else:
            raise ValueError(f"Unknown prior type: {spec[0]}")
    return float(lp)
@dataclass(frozen=True)
class InferenceProblem:
    """Bundle a dataset, a forward model, and systematics for inference."""

    x: Array
    y: Array
    sigma: Union[float, Array]
    model: Callable[[Array, Array], Array]  # model(theta, x)->mu
    param_names: Tuple[str, ...] = ()
    priors: Optional[Dict[str, PriorSpec]] = None
    A_nuisance: Optional[Array] = None
    nuisance_mean: Optional[Array] = None
    nuisance_cov: Optional[Array] = None

    def loglike(self, theta: Array) -> float:
        mu = _as_1d(self.model(_as_1d(theta), np.asarray(self.x)))
        y = _as_1d(self.y)
        cov_y = _cov_from_sigma(self.sigma, y.size)
        return marginal_loglike_additive_linear(
            y=y, mu=mu, cov_y=cov_y, A=self.A_nuisance, nu_mean=self.nuisance_mean, nu_cov=self.nuisance_cov
        )

    def logpost(self, theta: Array) -> float:
        lp = logprior(theta, self.priors, self.param_names or None)
        if not np.isfinite(lp):
            return -np.inf
        return lp + self.loglike(theta)
def metropolis_hastings(
    logp: Callable[[Array], float],
    x0: Array,
    nsteps: int,
    proposal_scale: Union[float, Array] = 0.1,
    rng: Optional[np.random.Generator] = None,
) -> Tuple[Array, Array, float]:
    """Random-walk Metropolis-Hastings sampler (Gaussian proposals)."""
    rng = np.random.default_rng() if rng is None else rng
    x = _as_1d(x0).copy()
    d = x.size
    s = np.asarray(proposal_scale, dtype=float)
    step = (np.ones(d) * float(s)) if s.ndim == 0 else s.reshape(-1)
    if step.size != d:
        raise ValueError("proposal_scale has wrong dimension")
    chain = np.empty((nsteps, d), dtype=float)
    lps = np.empty(nsteps, dtype=float)
    lp = float(logp(x))
    acc = 0
    for t in range(nsteps):
        prop = x + rng.normal(scale=step, size=d)
        lpp = float(logp(prop))
        if np.isfinite(lpp) and np.log(rng.random()) < (lpp - lp):
            x, lp = prop, lpp
            acc += 1
        chain[t], lps[t] = x, lp
    return chain, lps, acc / max(1, nsteps)
def summarize_chain(chain: Array, qs: Sequence[float] = (0.16, 0.5, 0.84)) -> Dict[str, Array]:
    chain = np.asarray(chain, dtype=float)
    if chain.ndim != 2:
        raise ValueError("chain must be (nsteps, ndim)")
    mean = chain.mean(axis=0)
    cov = np.cov(chain.T)
    quant = np.quantile(chain, qs, axis=0)
    return {"mean": mean, "cov": cov, "quantiles": quant}


def map_fit_random(
    logpost: Callable[[Array], float],
    bounds: Sequence[Tuple[float, float]],
    nsamples: int = 2000,
    rng: Optional[np.random.Generator] = None,
) -> Tuple[Array, float]:
    """Crude frequentist/MAP fit by random search within bounds."""
    rng = np.random.default_rng() if rng is None else rng
    lo = np.array([b[0] for b in bounds], dtype=float)
    hi = np.array([b[1] for b in bounds], dtype=float)
    best_x = lo.copy()
    best_lp = -np.inf
    for _ in range(int(nsamples)):
        x = lo + (hi - lo) * rng.random(size=lo.size)
        lp = float(logpost(x))
        if lp > best_lp:
            best_x, best_lp = x, lp
    return best_x, best_lp
