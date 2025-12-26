"""
pipeline package.

This package exposes a single public entrypoint (pipeline.main) used to run
experiments end-to-end. The implementation lives in pipeline.entrypoint.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

__all__ = ["main", "run"]
__version__ = "0.1.0"


def _load_main() -> Callable[..., Any]:
    # Import lazily so importing `pipeline` is lightweight and side-effect free.
    from .entrypoint import main as _main  # type: ignore
    return _main


def main(argv: Optional[list[str]] = None) -> int:
    """Run the pipeline end-to-end.

    Args:
        argv: Optional CLI-style argument list (excluding program name).

    Returns:
        Process-style exit code (0 for success).
    """
    return int(_load_main()(argv=argv))


def run(argv: Optional[list[str]] = None) -> int:
    """Alias for main(), convenient for programmatic use."""
    return main(argv=argv)


def __getattr__(name: str) -> Any:
    # Allow `from pipeline import main` even if imported before entrypoint exists.
    if name == "main":
        return main
    if name == "run":
        return run
    raise AttributeError(name)
