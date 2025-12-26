"""Repository tooling package.

This package exists to support `python -m tools.metadata_cli` execution and to
provide stable import paths for shared tooling modules (schema loading and
validation). Importing `tools` should be lightweight and side-effect free.
"""
from __future__ import annotations
__all__ = ["run_metadata_cli"]
def run_metadata_cli(argv: list[str] | None = None) -> int:
    """Programmatic entrypoint for the blessed metadata CLI.

    This avoids importing CLI modules at package import time while still offering
    a stable API for tests or external automation.
    """
    from .metadata_cli import main

    return int(main(argv))
