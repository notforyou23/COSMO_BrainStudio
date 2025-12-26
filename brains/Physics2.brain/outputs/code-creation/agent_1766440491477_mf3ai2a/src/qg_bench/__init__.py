"""qg_bench: a tiny benchmark format + runner.

This package provides:
- JSON Schema validation helpers for benchmark datasets.
- A minimal benchmark runner that produces deterministic JSON results.

The concrete implementations live in submodules (e.g., :mod:`qg_bench.validate`,
:mod:`qg_bench.runner`). This initializer exposes a small, stable public API.
"""
from __future__ import annotations

from importlib import metadata as _metadata
from typing import Any


def _detect_version() -> str:
    """Return the installed package version, or a safe fallback."""
    try:
        return _metadata.version("qg_bench")
    except _metadata.PackageNotFoundError:
        return "0.0.0"


__version__ = _detect_version()
__all__ = [
    "__version__",
    "load_schema",
    "validate_dataset",
    "validate_file",
    "run_benchmark",
    "main",
]
def __getattr__(name: str) -> Any:
    """Lazy attribute resolver for the public API.

    This avoids importing optional submodules at package import time and keeps
    startup overhead low.
    """
    if name in {"load_schema", "validate_dataset", "validate_file"}:
        from . import validate as _validate  # local import for laziness

        return getattr(_validate, name)
    if name in {"run_benchmark", "main"}:
        from . import runner as _runner  # local import for laziness

        return getattr(_runner, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
def __dir__() -> list[str]:
    return sorted(set(globals().keys()) | set(__all__))
