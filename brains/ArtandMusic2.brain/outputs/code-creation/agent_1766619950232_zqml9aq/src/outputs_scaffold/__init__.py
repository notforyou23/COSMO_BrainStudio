"""
outputs_scaffold: utilities to generate and validate an /outputs scaffold.

This package is intentionally lightweight; templates and generator logic live in
submodules and are imported lazily to keep imports deterministic and robust.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
__all__ = [
    "__version__",
    "get_version",
    "generate_outputs_scaffold",
    "validate_outputs_scaffold",
    "OutputsScaffoldError",
]

__version__ = "0.1.0"
class OutputsScaffoldError(RuntimeError):
    """Raised for errors during scaffold generation/validation."""
def get_version() -> str:
    """Return the package version."""
    return __version__
def _lazy_import_generator():
    try:
        from .generator import generate_outputs_scaffold, validate_outputs_scaffold  # type: ignore
    except Exception as e:  # pragma: no cover
        raise OutputsScaffoldError(
            "outputs_scaffold generator components are unavailable; "
            "ensure src/outputs_scaffold/generator.py is present and importable."
        ) from e
    return generate_outputs_scaffold, validate_outputs_scaffold
def generate_outputs_scaffold(
    project_root: str | "Path",
    outputs_dirname: str = "outputs",
    *,
    mode: str = "create",
    force: bool = False,
) -> Dict[str, Any]:
    """
    Create/initialize an outputs scaffold under project_root/outputs_dirname.

    Parameters
    ----------
    project_root: path-like
        Project root directory.
    outputs_dirname: str
        Name of the outputs directory (default "outputs").
    mode: str
        "create" or "validate" depending on generator implementation.
    force: bool
        If True, overwrite existing scaffold artifacts where appropriate.
    """
    gen, _val = _lazy_import_generator()
    return gen(project_root, outputs_dirname=outputs_dirname, mode=mode, force=force)
def validate_outputs_scaffold(
    project_root: str | "Path",
    outputs_dirname: str = "outputs",
    *,
    strict: bool = False,
) -> Dict[str, Any]:
    """
    Validate the outputs scaffold under project_root/outputs_dirname.

    Returns a report dict describing missing/outdated files, and references.
    """
    _gen, val = _lazy_import_generator()
    return val(project_root, outputs_dirname=outputs_dirname, strict=strict)
