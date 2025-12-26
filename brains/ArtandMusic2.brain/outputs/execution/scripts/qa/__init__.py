"""
scripts.qa package.

This package hosts QA automation helpers, including a diagnostic run mode designed
to reproduce failures with high telemetry and to iteratively remediate common
environment issues until a minimal test run completes and writes logs under
outputs/qa/logs/.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Union

__all__ = [
    "get_project_root",
    "get_logs_dir",
    "diagnostic_main",
    "run_diagnostic",
]


def get_project_root() -> Path:
    """Return the project root directory (the directory containing 'scripts')."""
    here = Path(__file__).resolve()
    # .../<root>/scripts/qa/__init__.py
    return here.parents[2]


def get_logs_dir() -> Path:
    """Return the canonical QA logs directory (created if missing)."""
    d = get_project_root() / "outputs" / "qa" / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


Argv = Optional[Union[Sequence[str], Iterable[str]]]


def diagnostic_main(argv: Argv = None) -> int:
    """Entry point for diagnostic QA mode (lazy import to keep package import light)."""
    from .diagnostic_run import main as _main  # type: ignore

    args: Optional[List[str]]
    if argv is None:
        args = None
    else:
        args = list(argv)
    return int(_main(args))


def run_diagnostic(argv: Argv = None) -> int:
    """Alias for diagnostic_main for backwards/forwards compatibility."""
    return diagnostic_main(argv)
