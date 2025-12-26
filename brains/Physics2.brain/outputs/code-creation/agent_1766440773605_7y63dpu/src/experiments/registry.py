"""Lightweight experiments registry.

This module is intentionally small and safe to import during `compileall`.
It provides a simple in-memory registry for experiment callables plus metadata.

Typical usage:

    from experiments.registry import register, get

    @register(name="my_exp", description="Demo")
    def run(seed: int = 0):
        ...

    spec = get("my_exp")
    spec.fn(seed=123)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
@dataclass(frozen=True)
class ExperimentSpec:
    """A registered experiment entry."""

    name: str
    fn: Callable[..., Any]
    description: str = ""
    tags: Tuple[str, ...] = ()
    default_params: Mapping[str, Any] = field(default_factory=dict)

    def call(self, **params: Any) -> Any:
        """Call the underlying experiment with merged default parameters."""
        merged: Dict[str, Any] = dict(self.default_params)
        merged.update(params)
        return self.fn(**merged)
_REGISTRY: Dict[str, ExperimentSpec] = {}


def register(
    fn: Optional[Callable[..., Any]] = None,
    *,
    name: Optional[str] = None,
    description: str = "",
    tags: Sequence[str] = (),
    default_params: Optional[Mapping[str, Any]] = None,
    overwrite: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register an experiment function.

    Can be used as a decorator or as a function:

        @register(name="exp1")
        def exp1(...): ...

        def exp2(...): ...
        register(exp2, name="exp2")

    Args:
        fn: The experiment callable (optional when used as a decorator).
        name: Registry key; defaults to fn.__name__.
        description: Human readable description.
        tags: Optional tags for grouping/filters.
        default_params: Default keyword arguments passed to the callable.
        overwrite: If True, allow replacing an existing entry.
    """

    def _do_register(func: Callable[..., Any]) -> Callable[..., Any]:
        exp_name = name or getattr(func, "__name__", None) or "experiment"
        if (not overwrite) and exp_name in _REGISTRY:
            raise KeyError(f"Experiment already registered: {exp_name}")
        spec = ExperimentSpec(
            name=exp_name,
            fn=func,
            description=description or "",
            tags=tuple(tags) if tags else (),
            default_params=dict(default_params or {}),
        )
        _REGISTRY[exp_name] = spec
        return func

    return _do_register(fn) if fn is not None else _do_register
def get(name: str) -> ExperimentSpec:
    """Retrieve a registered experiment spec by name."""
    try:
        return _REGISTRY[name]
    except KeyError as e:
        available = ", ".join(sorted(_REGISTRY)) or "<none>"
        raise KeyError(f"Unknown experiment: {name}. Available: {available}") from e


def list_experiments(*, tag: Optional[str] = None) -> List[ExperimentSpec]:
    """List registered experiments, optionally filtered by a single tag."""
    items = sorted(_REGISTRY.values(), key=lambda s: s.name)
    if tag is None:
        return items
    return [s for s in items if tag in s.tags]


def names(*, tag: Optional[str] = None) -> List[str]:
    """List registered experiment names."""
    return [s.name for s in list_experiments(tag=tag)]


def clear() -> None:
    """Clear the registry (primarily for tests)."""
    _REGISTRY.clear()


def register_many(
    specs: Iterable[Callable[..., Any]],
    *,
    overwrite: bool = False,
) -> List[str]:
    """Register multiple callables using their __name__ as the key."""
    out: List[str] = []
    for fn in specs:
        register(fn, overwrite=overwrite)
        out.append(getattr(fn, "__name__", "experiment"))
    return out
