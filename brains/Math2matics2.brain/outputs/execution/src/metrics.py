from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

import numpy as np


def _as_float64_1d(x: Any) -> np.ndarray:
    a = np.asarray(x, dtype=np.float64)
    if a.ndim != 1:
        a = a.reshape(-1)
    return a


def stable_mean(x: Any) -> float:
    a = _as_float64_1d(x)
    n = int(a.size)
    if n == 0:
        return float("nan")
    s = np.sum(a, dtype=np.float64)
    return float(s / np.float64(n))


def stable_median(x: Any) -> float:
    a = _as_float64_1d(x)
    n = int(a.size)
    if n == 0:
        return float("nan")
    b = np.sort(a, kind="mergesort")
    mid = n // 2
    if n % 2 == 1:
        return float(b[mid])
    return float((b[mid - 1] + b[mid]) * 0.5)


def _choose_mom_groups(n: int, num_groups: Optional[int], group_size: Optional[int]) -> Tuple[int, int]:
    if n <= 0:
        return (0, 0)
    if group_size is not None:
        gs = int(max(1, group_size))
        g = int((n + gs - 1) // gs)
        return (g, gs)
    if num_groups is not None:
        g = int(max(1, num_groups))
        gs = int(max(1, (n + g - 1) // g))
        return (g, gs)
    g = int(max(1, int(np.sqrt(n))))
    gs = int(max(1, (n + g - 1) // g))
    g = int((n + gs - 1) // gs)
    return (g, gs)


def median_of_means(x: Any, *, num_groups: Optional[int] = None, group_size: Optional[int] = None) -> float:
    a = _as_float64_1d(x)
    n = int(a.size)
    if n == 0:
        return float("nan")
    g, gs = _choose_mom_groups(n, num_groups, group_size)
    if g <= 1 or gs >= n:
        return stable_mean(a)

    means = np.empty(g, dtype=np.float64)
    start = 0
    for i in range(g):
        end = min(n, start + gs)
        if end <= start:
            means[i] = np.float64("nan")
        else:
            chunk = a[start:end]
            means[i] = np.sum(chunk, dtype=np.float64) / np.float64(chunk.size)
        start = end
    means = means[np.isfinite(means)]
    if means.size == 0:
        return float("nan")
    return stable_median(means)


def errors(estimate: Any, truth: float) -> Dict[str, float]:
    est = float(estimate)
    t = float(truth)
    e = est - t
    ae = abs(e)
    se = e * e
    return {"estimate": est, "error": e, "abs_error": ae, "squared_error": se}


def summarize_estimates(estimates: Any, truth: float) -> Dict[str, Any]:
    a = np.asarray(estimates, dtype=np.float64).reshape(-1)
    a = a[np.isfinite(a)]
    n = int(a.size)
    if n == 0:
        return {
            "n": 0,
            "truth": float(truth),
            "mean": float("nan"),
            "std": float("nan"),
            "bias": float("nan"),
            "mae": float("nan"),
            "mse": float("nan"),
            "rmse": float("nan"),
            "median": float("nan"),
            "q05": float("nan"),
            "q95": float("nan"),
        }

    t = np.float64(truth)
    mu = np.sum(a, dtype=np.float64) / np.float64(n)
    dif = a - mu
    var = np.sum(dif * dif, dtype=np.float64) / np.float64(max(1, n - 1))
    std = np.sqrt(var, dtype=np.float64)

    err = a - t
    bias = np.sum(err, dtype=np.float64) / np.float64(n)
    ae = np.abs(err)
    se = err * err
    mae = np.sum(ae, dtype=np.float64) / np.float64(n)
    mse = np.sum(se, dtype=np.float64) / np.float64(n)
    rmse = np.sqrt(mse, dtype=np.float64)

    b = np.sort(a, kind="mergesort")
    q05 = np.quantile(b, 0.05, method="linear") if hasattr(np, "quantile") else np.percentile(b, 5)
    q95 = np.quantile(b, 0.95, method="linear") if hasattr(np, "quantile") else np.percentile(b, 95)

    return {
        "n": n,
        "truth": float(truth),
        "mean": float(mu),
        "std": float(std),
        "bias": float(bias),
        "mae": float(mae),
        "mse": float(mse),
        "rmse": float(rmse),
        "median": float(stable_median(b)),
        "q05": float(q05),
        "q95": float(q95),
    }


def estimator_metrics(samples_2d: Any, truth: float, *, mom_groups: Optional[int] = None) -> Dict[str, Any]:
    x = np.asarray(samples_2d, dtype=np.float64)
    if x.ndim != 2:
        raise ValueError("samples_2d must be a 2D array shaped (n_trials, n_samples)")
    mean_est = np.apply_along_axis(stable_mean, 1, x)
    mom_est = np.apply_along_axis(lambda r: median_of_means(r, num_groups=mom_groups), 1, x)
    return {
        "mean": summarize_estimates(mean_est, truth),
        "median_of_means": summarize_estimates(mom_est, truth),
        "params": {"mom_groups": None if mom_groups is None else int(mom_groups)},
    }
