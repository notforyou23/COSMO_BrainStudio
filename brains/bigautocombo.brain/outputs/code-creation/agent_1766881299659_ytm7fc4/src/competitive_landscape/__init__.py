"""Competitive landscape overrides package.

This package exposes a small, stable public API for loading and validating
competitive landscape override YAML files while keeping implementation details
modular (see `overrides.py`, `overrides_schema.py`, and `yaml_support.py`).
"""
from __future__ import annotations

from importlib import import_module
from typing import Dict, Tuple

__all__ = [
    "load_overrides",
    "load_overrides_file",
    "load_overrides_files",
    "merge_overrides",
    "normalize_overrides",
    "validate_overrides",
    "OverridesValidationError",
    "OverridesConfig",
    "OverridesDocument",
    "load_yaml",
    "dump_yaml",
    "resolve_yaml_path",
]

_EXPORTS: Dict[str, Tuple[str, str]] = {
    # High-level overrides API
    "load_overrides": (".overrides", "load_overrides"),
    "load_overrides_file": (".overrides", "load_overrides_file"),
    "load_overrides_files": (".overrides", "load_overrides_files"),
    "merge_overrides": (".overrides", "merge_overrides"),
    "normalize_overrides": (".overrides", "normalize_overrides"),
    # Schema / validation
    "validate_overrides": (".overrides_schema", "validate_overrides"),
    "OverridesValidationError": (".overrides_schema", "OverridesValidationError"),
    "OverridesConfig": (".overrides_schema", "OverridesConfig"),
    "OverridesDocument": (".overrides_schema", "OverridesDocument"),
    # YAML support utilities
    "load_yaml": (".yaml_support", "load_yaml"),
    "dump_yaml": (".yaml_support", "dump_yaml"),
    "resolve_yaml_path": (".yaml_support", "resolve_yaml_path"),
}


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_rel, attr = _EXPORTS[name]
    module = import_module(module_rel, __name__)
    value = getattr(module, attr)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals().keys()) | set(_EXPORTS.keys()))
