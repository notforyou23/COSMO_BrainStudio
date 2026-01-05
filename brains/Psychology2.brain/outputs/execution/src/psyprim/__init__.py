"""psyprim: standardized workflows + lightweight tooling for primary-source scholarship in psychology.

This package exposes:
- __version__: installed package version
- Convenience re-exports via lazy imports (PEP 562) for primary public interfaces
"""
from __future__ import annotations

from importlib import metadata as _metadata
from typing import Any, Dict, Tuple


def _get_version() -> str:
    try:
        return _metadata.version("psyprim")
    except _metadata.PackageNotFoundError:
        return "0.0.0"


__version__ = _get_version()


# Lazy re-exports to keep import side-effects minimal and to avoid hard failures
# during partial installs or when optional deps (e.g., CLI) are not present.
_LAZY_ATTRS: Dict[str, Tuple[str, str]] = {
    # CLI entrypoints
    "app": ("psyprim.cli", "app"),
    "main": ("psyprim.cli", "main"),
    # Pydantic models (common public names; resolved at runtime if present)
    "PrimarySourceRecord": ("psyprim.models", "PrimarySourceRecord"),
    "SourceRecord": ("psyprim.models", "SourceRecord"),
    "EditionProvenance": ("psyprim.models", "EditionProvenance"),
    "TranslationProvenance": ("psyprim.models", "TranslationProvenance"),
    "VariantPagination": ("psyprim.models", "VariantPagination"),
    "PublicDomainCitation": ("psyprim.models", "PublicDomainCitation"),
    "PublicDomainStatus": ("psyprim.models", "PublicDomainStatus"),
    "Citation": ("psyprim.models", "Citation"),
    "Provenance": ("psyprim.models", "Provenance"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_ATTRS:
        module_name, attr_name = _LAZY_ATTRS[name]
        module = __import__(module_name, fromlist=[attr_name])
        try:
            value = getattr(module, attr_name)
        except AttributeError as e:
            raise AttributeError(f"module '{module_name}' has no attribute '{attr_name}'") from e
        globals()[name] = value
        return value
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + list(_LAZY_ATTRS.keys()))


__all__ = ["__version__", *_LAZY_ATTRS.keys()]
