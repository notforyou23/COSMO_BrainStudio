"""build_pipeline package.

Public API:
- run_pipeline: Run schema validation + placeholder meta-analysis + build logging.
- main: Console-script compatible entrypoint.

This package is designed to be used both as a library and as a CLI entrypoint.
"""
from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as _pkg_version
def get_version(dist_name: str = "build_pipeline") -> str:
    """Return the installed distribution version, or a sensible default."""
    try:
        return _pkg_version(dist_name)
    except PackageNotFoundError:
        return "0.0.0+local"
__version__ = get_version()

__all__ = [
    "__version__",
    "get_version",
    "main",
    "run_pipeline",
]

# Lazy imports to avoid importing heavier modules at package import time.
def run_pipeline(argv: list[str] | None = None) -> int:
    """Run the full build pipeline (library entrypoint)."""
    from .cli import run_pipeline as _run

    return _run(argv)


def main() -> int:
    """Console-script compatible entrypoint."""
    from .cli import main as _main

    return _main()
