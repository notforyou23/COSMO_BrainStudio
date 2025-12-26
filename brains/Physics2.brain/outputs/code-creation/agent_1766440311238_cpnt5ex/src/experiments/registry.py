"""Experiment registry used by the CLI.

The registry maps stable experiment names to callables plus a default parameter
set. Callables are plain Python functions that accept keyword parameters and
return a JSON-serializable dict (recommended keys: 'summary', 'artifacts').
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, List, Optional, Tuple


JSONDict = Dict[str, Any]
ExperimentFn = Callable[..., JSONDict]


@dataclass(frozen=True)
class ExperimentSpec:
    """Metadata for one experiment."""

    name: str
    fn: ExperimentFn
    defaults: Mapping[str, Any]
    description: str = ""


def _require(pkg: str) -> None:
    try:
        __import__(pkg)
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            f"Experiment requires optional dependency '{pkg}'. Install it first."
        ) from e


def exp_logistic_map(r: float = 3.7, x0: float = 0.2, n: int = 2000, burn: int = 200) -> JSONDict:
    """Iterate the logistic map and report basic statistics after burn-in."""
    _require("numpy")
    import numpy as np

    x = float(x0)
    xs = np.empty(int(n), dtype=float)
    for i in range(int(n)):
        x = float(r) * x * (1.0 - x)
        xs[i] = x
    tail = xs[int(burn) :]
    return {
        "summary": {
            "r": float(r),
            "x0": float(x0),
            "n": int(n),
            "burn": int(burn),
            "mean": float(np.mean(tail)),
            "std": float(np.std(tail)),
            "min": float(np.min(tail)),
            "max": float(np.max(tail)),
        }
    }


def exp_taylor_sin(order: int = 9, x: float = 1.0) -> JSONDict:
    """Symbolically form the Taylor polynomial for sin(x) and compare numerically."""
    _require("sympy")
    import sympy as sp

    x_sym = sp.Symbol("x")
    poly = sp.series(sp.sin(x_sym), x_sym, 0, int(order) + 1).removeO()
    approx = float(poly.subs({x_sym: float(x)}).evalf())
    true = float(sp.sin(float(x)))
    return {
        "summary": {
            "order": int(order),
            "x": float(x),
            "poly": str(sp.simplify(poly)),
            "approx": approx,
            "true": true,
            "abs_error": abs(true - approx),
        }
    }


def exp_newton_sqrt(a: float = 2.0, x0: float = 1.0, n: int = 8) -> JSONDict:
    """Newton iterations for sqrt(a) and the observed quadratic convergence."""
    a = float(a)
    x = float(x0)
    iters: List[Tuple[int, float, float]] = []
    for k in range(int(n)):
        err = abs(x - a ** 0.5)
        iters.append((k, x, err))
        x = 0.5 * (x + a / x)
    err = abs(x - a ** 0.5)
    iters.append((int(n), x, err))
    return {
        "summary": {"a": a, "x0": float(x0), "n": int(n)},
        "iterations": [{"k": k, "x": xv, "abs_error": ev} for k, xv, ev in iters],
    }


_REGISTRY: Dict[str, ExperimentSpec] = {
    "logistic_map": ExperimentSpec(
        name="logistic_map",
        fn=exp_logistic_map,
        defaults={"r": 3.7, "x0": 0.2, "n": 2000, "burn": 200},
        description="Iterate x_{n+1}=r x_n (1-x_n) and summarize tail statistics.",
    ),
    "taylor_sin": ExperimentSpec(
        name="taylor_sin",
        fn=exp_taylor_sin,
        defaults={"order": 9, "x": 1.0},
        description="Symbolic Taylor polynomial for sin(x) with numeric error.",
    ),
    "newton_sqrt": ExperimentSpec(
        name="newton_sqrt",
        fn=exp_newton_sqrt,
        defaults={"a": 2.0, "x0": 1.0, "n": 8},
        description="Newton iterations for sqrt(a) with per-iteration error.",
    ),
}


def list_experiments() -> List[str]:
    """Return experiment names in a stable order."""
    return sorted(_REGISTRY.keys())


def get_spec(name: str) -> ExperimentSpec:
    """Return the ExperimentSpec for a registered name."""
    try:
        return _REGISTRY[name]
    except KeyError as e:
        raise KeyError(f"Unknown experiment '{name}'. Available: {', '.join(list_experiments())}") from e


def get_callable(name: str) -> ExperimentFn:
    """Return the experiment callable for a registered name."""
    return get_spec(name).fn


def get_defaults(name: str) -> Mapping[str, Any]:
    """Return default parameters for a registered name."""
    return dict(get_spec(name).defaults)


__all__ = [
    "ExperimentSpec",
    "ExperimentFn",
    "list_experiments",
    "get_spec",
    "get_callable",
    "get_defaults",
]
