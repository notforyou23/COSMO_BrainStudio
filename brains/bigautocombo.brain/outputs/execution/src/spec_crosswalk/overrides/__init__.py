"""Overrides package public API.

This module provides a stable import surface while allowing internal refactors.
It prefers the new module layout (schema/apply/yaml_support) and transparently
falls back to legacy module names when needed.
"""
from __future__ import annotations

from importlib import import_module
from types import ModuleType
from typing import Any, Dict, Iterable, Optional, Tuple

__all__ = [
    "schema",
    "apply",
    "yaml_support",
]
_MODULE_CANDIDATES: Dict[str, Tuple[str, ...]] = {
    "schema": (".schema", ".overrides_schema"),
    "apply": (".apply", ".overrides"),
    "yaml_support": (".yaml_support",),
}

_EXPORTED_NAMES: Tuple[str, ...] = (
    "Overrides",
    "Override",
    "OverrideRule",
    "OverrideSet",
    "OverrideOp",
    "OverrideOperation",
    "OverridePath",
    "OverrideTarget",
    "OverridesSchema",
    "OverridesModel",
    "OverridesConfig",
    "apply_overrides",
    "apply_override",
    "validate_overrides",
    "validate_override",
    "load_overrides_yaml",
    "dump_overrides_yaml",
    "loads_overrides_yaml",
    "dumps_overrides_yaml",
    "yaml_load",
    "yaml_dump",
)


def _import_first(candidates: Iterable[str]) -> Optional[ModuleType]:
    for mod in candidates:
        try:
            return import_module(mod, __name__)
        except Exception:
            continue
    return None


schema = _import_first(_MODULE_CANDIDATES["schema"])
apply = _import_first(_MODULE_CANDIDATES["apply"])
yaml_support = _import_first(_MODULE_CANDIDATES["yaml_support"])
def _resolve_attr(name: str) -> Any:
    # Prefer explicitly exported API names from known modules.
    for m in (schema, apply, yaml_support):
        if m is not None and hasattr(m, name):
            return getattr(m, name)
    # Fallback: try importing candidates again in case modules were added later.
    for key, candidates in _MODULE_CANDIDATES.items():
        m = globals().get(key)
        if m is None:
            m = _import_first(candidates)
            globals()[key] = m
        if m is not None and hasattr(m, name):
            return getattr(m, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __getattr__(name: str) -> Any:  # PEP 562
    value = _resolve_attr(name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    base = set(globals().keys())
    base.update(__all__)
    base.update(_EXPORTED_NAMES)
    for m in (schema, apply, yaml_support):
        if m is not None:
            base.update(getattr(m, "__all__", ()))
    return sorted(base)
def _export_public_names() -> None:
    # Eagerly bind common API symbols when available (keeps help()/dir() friendly).
    for name in _EXPORTED_NAMES:
        try:
            globals()[name] = _resolve_attr(name)
        except AttributeError:
            pass


_export_public_names()
__all__ = sorted(set(__all__) | {n for n in _EXPORTED_NAMES if n in globals()})
