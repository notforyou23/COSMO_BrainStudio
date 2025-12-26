"""Experiments package.

This package groups small, reproducible numerical/symbolic experiments and exposes a
stable public interface for discovery and execution via the experiment registry.

The registry implementation lives in :mod:`experiments.registry` (added in later
stages). This module keeps imports lightweight by delegating to that module at
call time rather than import time.
""""
from __future__ import annotations

from importlib import import_module
from types import ModuleType
from typing import Any, Callable, Iterable, Mapping, Sequence, TypeVar, overload

__all__ = [
    "registry_module",
    "list_experiments",
    "get_experiment",
    "run_experiment",
    "register_experiment",
]
T = TypeVar("T")


def registry_module() -> ModuleType:
    """Return the loaded :mod:`experiments.registry` module.

    The import is performed lazily to keep ``import experiments`` fast and to
    avoid importing optional heavy dependencies unless an experiment is invoked.
    """
    return import_module(__name__ + ".registry")
def _get_attr(mod: ModuleType, *names: str) -> Any:
    for n in names:
        if hasattr(mod, n):
            return getattr(mod, n)
    raise AttributeError(
        f"{mod.__name__} does not define any of {names}. "  # pragma: no cover
        "Ensure src/experiments/registry.py exports the expected symbols."
    )


def list_experiments() -> Sequence[str]:
    """List registered experiment identifiers."""
    mod = registry_module()
    fn = _get_attr(mod, "list_experiments", "available_experiments")
    return list(fn())


def get_experiment(experiment_id: str) -> Any:
    """Fetch a registered experiment spec/callable by id."""
    mod = registry_module()
    fn = _get_attr(mod, "get_experiment", "lookup_experiment")
    return fn(experiment_id)


def run_experiment(experiment_id: str, /, **kwargs: Any) -> Mapping[str, Any]:
    """Run an experiment by id and return its structured result.

    Parameters
    ----------
    experiment_id:
        Registry key identifying the experiment.
    **kwargs:
        Experiment-specific parameters; forwarded to the registry.
    """
    mod = registry_module()
    fn = _get_attr(mod, "run_experiment", "run")
    return fn(experiment_id, **kwargs)


def register_experiment(*args: Any, **kwargs: Any) -> Any:
    """Decorator/function to register an experiment with the global registry.

    This delegates to :func:`experiments.registry.register_experiment` (or an
    equivalent symbol) and is intended to be used by experiment modules.
    """
    mod = registry_module()
    reg = _get_attr(mod, "register_experiment", "register")
    return reg(*args, **kwargs)
