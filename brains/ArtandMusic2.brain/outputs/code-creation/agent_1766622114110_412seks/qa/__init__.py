"""QA gate package.

Exposes a stable, import-friendly API and supports module execution patterns
(e.g., `python -m qa.run`) by providing a public `run` callable.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Union


__all__ = ["run", "main", "__version__"]
__version__ = "0.1.0"


def run(argv: Optional[Sequence[str]] = None) -> int:
    """Run the QA gate CLI.

    Parameters
    ----------
    argv:
        Optional argument vector (excluding the program name). If None, uses
        sys.argv[1:].

    Returns
    -------
    int
        Process exit code (0 on success, non-zero on failure).
    """
    from .run import main as _main

    return _main(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Alias for run(), intended for conventional CLI entrypoints."""
    return run(argv)
