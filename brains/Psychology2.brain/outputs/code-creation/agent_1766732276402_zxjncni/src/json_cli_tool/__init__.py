"""
json_cli_tool package.

This package provides a small CLI to run the artifact gate and taxonomy validator
against the project's generated artifacts and to write console + structured JSON logs.
"""
from __future__ import annotations

from .version import __version__, get_version
# Public CLI entrypoints. These imports are best-effort so that importing the
# package for version metadata does not require CLI dependencies at import time.
try:
    from .cli import main as cli_main  # type: ignore
except Exception:  # pragma: no cover
    cli_main = None  # type: ignore

try:
    from .cli import run as run_artifact_gate_and_taxonomy_validator  # type: ignore
except Exception:  # pragma: no cover
    run_artifact_gate_and_taxonomy_validator = None  # type: ignore
__all__ = [
    "__version__",
    "get_version",
    "cli_main",
    "run_artifact_gate_and_taxonomy_validator",
]
