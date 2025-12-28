"""protocol_planner

Tools to generate community-endorsed protocol drafts and implementation plans for
provenance-aware primary-source psychology scholarship.

Public API:
- cli_main: callable CLI entry point (used by console_scripts)
- __version__: package version string
"""

from __future__ import annotations

__all__ = ["__version__", "cli_main"]

__version__ = "0.1.0"


def cli_main(argv: list[str] | None = None) -> int:
    """Run the command-line interface.

    Parameters
    ----------
    argv:
        Optional argument list (excluding program name). If None, arguments are
        read from sys.argv by the CLI module.

    Returns
    -------
    int
        Process exit code (0 for success).
    """
    from .cli import main as _main

    return int(_main(argv))
