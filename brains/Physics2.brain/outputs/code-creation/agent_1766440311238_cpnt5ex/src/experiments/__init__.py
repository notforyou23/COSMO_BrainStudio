"""Experiment package initializer.

This module exposes a lightweight registry for numerical/symbolic experiment
routines. Experiments are ordinary callables (typically functions) registered
under a string name.

Typical usage:

    from experiments import register_experiment, get_experiment, list_experiments

    @register_experiment("my_experiment")
    def run(...):
        ...

    get_experiment("my_experiment")(...)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Sequence, Tuple
ExperimentFn = Callable[..., Any]
@dataclass(frozen=True)
class ExperimentSpec:
    """Metadata + callable for a registered experiment."""

    name: str
    fn: ExperimentFn
    description: str = ""
    tags: Tuple[str, ...] = ()
_REGISTRY: Dict[str, ExperimentSpec] = {}
def register_experiment(
    name: str,
    *,
    description: str = "",
    tags: Sequence[str] = (),
    overwrite: bool = False,
) -> Callable[[ExperimentFn], ExperimentFn]:
    """Decorator to register an experiment.

    Parameters
    ----------
    name:
        Unique experiment identifier.
    description:
        Short human-readable description.
    tags:
        Optional categorization tags.
    overwrite:
        If True, replace an existing registration.
    """

    def _decorator(fn: ExperimentFn) -> ExperimentFn:
        if not overwrite and name in _REGISTRY:
            raise KeyError(f"Experiment already registered: {name}")
        _REGISTRY[name] = ExperimentSpec(
            name=name, fn=fn, description=description, tags=tuple(tags)
        )
        return fn

    return _decorator
def add_experiment(
    name: str,
    fn: ExperimentFn,
    *,
    description: str = "",
    tags: Sequence[str] = (),
    overwrite: bool = False,
) -> None:
    """Register an experiment without using decorator syntax."""
    register_experiment(
        name, description=description, tags=tags, overwrite=overwrite
    )(fn)
def get_experiment(name: str) -> ExperimentFn:
    """Return the callable for *name* or raise KeyError."""
    return _REGISTRY[name].fn
def get_spec(name: str) -> ExperimentSpec:
    """Return the ExperimentSpec for *name* or raise KeyError."""
    return _REGISTRY[name]
def list_experiments(*, tag: Optional[str] = None) -> Tuple[str, ...]:
    """List registered experiment names, optionally filtered by tag."""
    if tag is None:
        return tuple(sorted(_REGISTRY))
    return tuple(sorted(n for n, s in _REGISTRY.items() if tag in s.tags))
def registry() -> Mapping[str, ExperimentSpec]:
    """Read-only view of the current registry."""
    return _REGISTRY
def describe_experiments(names: Optional[Iterable[str]] = None) -> Dict[str, Dict[str, Any]]:
    """Return structured descriptions suitable for printing/JSON."""
    if names is None:
        items = _REGISTRY.items()
    else:
        items = ((n, _REGISTRY[n]) for n in names)
    return {
        n: {"description": s.description, "tags": list(s.tags), "callable": getattr(s.fn, "__name__", "<callable>")}
        for n, s in items
    }
__all__ = [
    "ExperimentSpec",
    "ExperimentFn",
    "add_experiment",
    "describe_experiments",
    "get_experiment",
    "get_spec",
    "list_experiments",
    "register_experiment",
    "registry",
]
