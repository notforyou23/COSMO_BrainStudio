"""
Canonical runner package.

This package provides the single canonical runner entrypoint and supporting
utilities for executing configured commands (typically via Docker) while
persisting stable log/config/env artifacts and a run summary for downstream
evaluation.

Public API is intentionally small:
- run(): convenience wrapper around the canonical entrypoint's run().
- load_entrypoint(): returns the canonical entrypoint module (lazy import).
- RunnerConfig / RunSummary: typed models for configuration and run summary.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, Optional, Sequence, Mapping

__all__ = [
    "run",
    "load_entrypoint",
    "RunnerConfig",
    "RunSummary",
    "ContainerLost",
    "RunnerResult",
]

__version__ = "0.1.0"
def load_entrypoint():
    """
    Lazily import and return the canonical entrypoint module.

    Laziness avoids importing Docker-related dependencies during simple metadata
    operations (e.g., help/version) and keeps package import side effects minimal.
    """
    return import_module("src.runner.entrypoint")
def run(
    argv: Optional[Sequence[str]] = None,
    *,
    env: Optional[Mapping[str, str]] = None,
    config: Optional[Any] = None,
) -> Any:
    """
    Convenience wrapper for the canonical runner entrypoint.

    Parameters:
        argv: CLI-style argv list (excluding program name) or None to use sys.argv.
        env: Optional environment mapping override for the run.
        config: Optional configuration object/dict; forwarded to entrypoint if supported.

    Returns:
        Entry-point-defined result (typically a RunSummary or exit code).
    """
    ep = load_entrypoint()
    fn = getattr(ep, "run", None)
    if not callable(fn):
        raise RuntimeError("Canonical runner entrypoint missing callable 'run'.")
    try:
        return fn(argv=argv, env=env, config=config)
    except TypeError:
        # Back-compat: allow entrypoints that don't accept the newer kwargs.
        if config is not None or env is not None:
            return fn(argv=argv)
        return fn(argv=argv)
# Re-export models if available; keep import failures soft to allow staged builds.
try:
    from .models import RunnerConfig, RunSummary, ContainerLost, RunnerResult  # type: ignore
except Exception:  # pragma: no cover
    RunnerConfig = None  # type: ignore
    RunSummary = None  # type: ignore
    ContainerLost = None  # type: ignore
    RunnerResult = None  # type: ignore
