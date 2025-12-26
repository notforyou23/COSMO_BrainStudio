"""refactor_modularize package.

This package provides a small toolchain to analyze a set of generated artifacts
(prompts, READMEs, config files, etc.), refactor repeated fragments into
reusable modules, and export the results in a deterministic layout.

The public API is intentionally surfaced at the package root. Imports are
performed lazily to keep package import side effects minimal and to allow tools
to depend on only the pieces they need.
"""
from __future__ import annotations

from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any, Dict, Tuple
__all__ = [
    "__version__",
    # artifacts
    "Artifact",
    "ArtifactKind",
    "ArtifactMeta",
    "ArtifactSet",
    "load_artifacts",
    # refactor
    "RefactorEngine",
    "RefactorResult",
    # export
    "ExportPlan",
    "export_refactored",
    # cli
    "main",
]
try:
    __version__ = version("refactor_modularize")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"
# Map public attributes to (module, symbol) for lazy resolution.
_LAZY_EXPORTS: Dict[str, Tuple[str, str]] = {
    # artifacts
    "Artifact": ("refactor_modularize.artifacts", "Artifact"),
    "ArtifactKind": ("refactor_modularize.artifacts", "ArtifactKind"),
    "ArtifactMeta": ("refactor_modularize.artifacts", "ArtifactMeta"),
    "ArtifactSet": ("refactor_modularize.artifacts", "ArtifactSet"),
    "load_artifacts": ("refactor_modularize.artifacts", "load_artifacts"),
    # refactor
    "RefactorEngine": ("refactor_modularize.refactor", "RefactorEngine"),
    "RefactorResult": ("refactor_modularize.refactor", "RefactorResult"),
    # export
    "ExportPlan": ("refactor_modularize.export", "ExportPlan"),
    "export_refactored": ("refactor_modularize.export", "export_refactored"),
    # cli
    "main": ("refactor_modularize.cli", "main"),
}
def __getattr__(name: str) -> Any:
    """Resolve public attributes lazily.

    This keeps `import refactor_modularize` lightweight while still providing
    a convenient, flat public API.
    """
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    mod_name, sym_name = target
    module = import_module(mod_name)
    value = getattr(module, sym_name)
    globals()[name] = value  # cache for subsequent lookups
    return value
def __dir__() -> list[str]:
    return sorted(set(globals().keys()) | set(_LAZY_EXPORTS.keys()))
if TYPE_CHECKING:  # pragma: no cover
    from .artifacts import Artifact, ArtifactKind, ArtifactMeta, ArtifactSet, load_artifacts
    from .export import ExportPlan, export_refactored
    from .refactor import RefactorEngine, RefactorResult
    from .cli import main
