"""Experiment registry with CLI-discoverable metadata.

This module defines a small, dependency-light registry so experiments (numerical
toy models or symbolic derivations) can expose standardized metadata and a
uniform execution interface.

An experiment entrypoint is a dotted path: "pkg.mod:function". The function is
called as: fn(params: dict, *, seed: int|None=None, out_dir: Path|None=None) -> dict
and should return a JSON-serializable dict with results/artifacts.
""""
from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Tuple
@dataclass(frozen=True)
class ExperimentSpec:
    name: str
    summary: str
    entrypoint: str  # "module:function"
    inputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    tags: Tuple[str, ...] = ()
    details: str = ""
    version: str = "0"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "summary": self.summary,
            "details": self.details,
            "version": self.version,
            "entrypoint": self.entrypoint,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "tags": list(self.tags),
        }
_REGISTRY: Dict[str, ExperimentSpec] = {}


def register(spec: ExperimentSpec) -> ExperimentSpec:
    """Register an experiment spec (idempotent by name)."""
    if not spec.name or "/" in spec.name or " " in spec.name:
        raise ValueError(f"Invalid experiment name: {spec.name!r}")
    _REGISTRY[spec.name] = spec
    return spec


def registered(name: str, summary: str, entrypoint: str, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to register a function as an experiment entrypoint."""
    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        mod = fn.__module__
        ep = entrypoint or f"{mod}:{fn.__name__}"
        register(ExperimentSpec(name=name, summary=summary, entrypoint=ep, **kwargs))
        return fn
    return deco
def list_specs(*, tag: Optional[str] = None) -> List[ExperimentSpec]:
    specs = sorted(_REGISTRY.values(), key=lambda s: s.name)
    return [s for s in specs if (tag is None or tag in s.tags)]


def get_spec(name: str) -> ExperimentSpec:
    try:
        return _REGISTRY[name]
    except KeyError as e:
        raise KeyError(f"Unknown experiment {name!r}. Available: {sorted(_REGISTRY)}") from e


def _load_callable(entrypoint: str) -> Callable[..., Any]:
    if ":" not in entrypoint:
        raise ValueError(f"Invalid entrypoint {entrypoint!r}; expected 'module:function'")
    mod, fn = entrypoint.split(":", 1)
    return getattr(import_module(mod), fn)
def _apply_defaults(inputs: Mapping[str, Mapping[str, Any]], params: Mapping[str, Any]) -> Dict[str, Any]:
    out = dict(params)
    for k, spec in inputs.items():
        if k not in out and "default" in spec:
            out[k] = spec["default"]
    return out


def _validate_minimal(inputs: Mapping[str, Mapping[str, Any]], params: Mapping[str, Any]) -> None:
    for k, spec in inputs.items():
        if spec.get("required") and k not in params:
            raise ValueError(f"Missing required param: {k}")
        if k in params and "type" in spec:
            t = spec["type"]
            ok = True
            v = params[k]
            if t == "int": ok = isinstance(v, int) and not isinstance(v, bool)
            elif t == "float": ok = isinstance(v, (int, float)) and not isinstance(v, bool)
            elif t == "str": ok = isinstance(v, str)
            elif t == "bool": ok = isinstance(v, bool)
            elif t == "list": ok = isinstance(v, list)
            elif t == "dict": ok = isinstance(v, dict)
            if not ok:
                raise TypeError(f"Param {k} expected {t}, got {type(v).__name__}")
def run(name: str, params: Optional[Mapping[str, Any]] = None, *, seed: Optional[int] = None, out_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Run an experiment by name and return a standardized result dict."""
    spec = get_spec(name)
    call = _load_callable(spec.entrypoint)
    p = _apply_defaults(spec.inputs, params or {})
    _validate_minimal(spec.inputs, p)
    res = call(p, seed=seed, out_dir=Path(out_dir) if out_dir is not None else None)
    if not isinstance(res, dict):
        raise TypeError(f"Experiment {name!r} returned {type(res).__name__}, expected dict")
    return {"experiment": spec.as_dict(), "params": p, "result": res}


def export_metadata() -> List[Dict[str, Any]]:
    """JSON-ready metadata list for CLI discovery."""
    return [s.as_dict() for s in list_specs()]


__all__ = ["ExperimentSpec", "register", "registered", "list_specs", "get_spec", "run", "export_metadata"]
