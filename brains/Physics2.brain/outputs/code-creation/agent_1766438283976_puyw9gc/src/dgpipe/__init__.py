"""dgpipe package.

This module is the package entrypoint and public API surface. It is intentionally
lightweight: it avoids importing submodules at import time to prevent side
effects and to keep import costs low.

Public objects are exposed via lazy attribute access (PEP 562)."""
from __future__ import annotations
from importlib import metadata as _metadata
def _read_version() -> str:
    \"\"\"Return the installed package version, or a safe fallback.\"\"\"
    try:
        return _metadata.version("dgpipe")
    except _metadata.PackageNotFoundError:
        # Running from source (not installed) or during tooling.
        return "0.0.0"
__version__ = _read_version()
def version() -> str:
    \"\"\"Convenience accessor for :data:`__version__`.\"\"\"
    return __version__
# Lazy exports: map public attribute names to (module, attribute).
# These modules are expected to exist in the full project, but are not imported
# eagerly to keep this entrypoint side-effect free.
_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    # models
    "PipelineSpec": ("dgpipe.models", "PipelineSpec"),
    "StageSpec": ("dgpipe.models", "StageSpec"),
    "StageResult": ("dgpipe.models", "StageResult"),
    "PipelineResult": ("dgpipe.models", "PipelineResult"),
    "RunConfig": ("dgpipe.models", "RunConfig"),
    # protocols
    "Stage": ("dgpipe.protocols", "Stage"),
    "Runner": ("dgpipe.protocols", "Runner"),
    "ArtifactStore": ("dgpipe.protocols", "ArtifactStore"),
    "Logger": ("dgpipe.protocols", "Logger"),
}
__all__ = ["__version__", "version", *_LAZY_EXPORTS.keys()]
def __getattr__(name: str):
    \"\"\"Dynamically import exported objects on first access.

    This allows users to import from the package root (e.g. ``from dgpipe import
    PipelineSpec``) without importing submodules during ``import dgpipe``.
    \"\"\"
    try:
        module_name, attr_name = _LAZY_EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module 'dgpipe' has no attribute {name!r}") from exc

    from importlib import import_module

    module = import_module(module_name)
    try:
        value = getattr(module, attr_name)
    except AttributeError as exc:
        raise AttributeError(
            f"Lazy export {name!r} not found as {module_name}.{attr_name}"
        ) from exc
    globals()[name] = value  # cache for subsequent lookups
    return value
def __dir__() -> list[str]:
    \"\"\"Return a helpful list of attributes for introspection tools.\"\"\"
    return sorted(list(globals().keys()) + list(_LAZY_EXPORTS.keys()))
