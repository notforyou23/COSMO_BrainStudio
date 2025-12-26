"""
blessed_pipeline package entrypoint.

This package exposes a single "blessed" pipeline implementation as the stable,
supported public API surface. All imports should go through this package.
"""
from __future__ import annotations
from importlib.metadata import PackageNotFoundError, version as _pkg_version
try:
    __version__ = _pkg_version("generated_library_1766554417357")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"
# Public API re-exports
try:
    from .pipeline import Pipeline, PipelineConfig, run_pipeline
except Exception as _e:  # pragma: no cover
    raise ImportError(
        "Failed to import the blessed pipeline implementation. "
        "Ensure 'blessed_pipeline.pipeline' is present and free of syntax errors."
    ) from _e
__all__ = [
    "Pipeline",
    "PipelineConfig",
    "run_pipeline",
    "__version__",
]
