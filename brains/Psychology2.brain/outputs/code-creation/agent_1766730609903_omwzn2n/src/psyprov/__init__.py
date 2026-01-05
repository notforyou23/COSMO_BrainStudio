"""
psyprov: community-oriented planning toolkit for provenance-aware primary-source
scholarship workflows in psychology.

This package exposes:
- schemas: metadata models + JSON Schema exporters
- heuristics: lightweight provenance/variant/repository detection helpers
- plan generator: structured task breakdown + evaluation protocol scaffolding
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, Dict, List

__version__ = "0.1.0"


def _safe_import(module: str, names: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    try:
        m = import_module(module, package=__name__)
    except Exception:
        return out
    for n in names:
        if hasattr(m, n):
            out[n] = getattr(m, n)
    return out


# Eagerly expose what exists; future stages may add additional modules/symbols.
_exports: Dict[str, Any] = {}
_exports.update(
    _safe_import(
        f"{__name__}.schemas",
        [
            "EditionProvenance",
            "TranslationProvenance",
            "VariantLocator",
            "RepositoryCitation",
            "ProvenanceRecord",
            "export_json_schema",
            "export_all_json_schemas",
        ],
    )
)
_exports.update(
    _safe_import(
        f"{__name__}.heuristics",
        [
            "detect_repository_from_url",
            "detect_repository_from_text",
            "infer_language",
            "infer_edition_signals",
            "infer_translation_signals",
            "infer_locator_signals",
            "score_provenance_confidence",
        ],
    )
)
_exports.update(
    _safe_import(
        f"{__name__}.planner",
        [
            "PlanSpec",
            "generate_plan",
            "generate_validation_protocol",
            "generate_checklists",
        ],
    )
)

__all__ = sorted(_exports.keys())


def __getattr__(name: str) -> Any:
    if name in _exports:
        return _exports[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> List[str]:
    return sorted(set(globals().keys()) | set(__all__))


def public_api() -> Dict[str, Any]:
    """Return a snapshot of the currently available public symbols."""
    return dict(_exports)
