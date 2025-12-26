"""
Roadmap tooling package.

This package is intentionally lightweight: it exists primarily as a package marker
so `scripts.*` modules can be reliably imported when executing locally.

It also exposes a few small helpers used by scripts to resolve paths relative to
the repository root (the directory containing this `scripts/` package).
"""

from __future__ import annotations

from pathlib import Path

__all__ = [
    "PACKAGE_DIR",
    "PROJECT_ROOT",
    "OUTPUTS_DIR",
    "resolve_in_project",
]

PACKAGE_DIR: Path = Path(__file__).resolve().parent
PROJECT_ROOT: Path = PACKAGE_DIR.parent
OUTPUTS_DIR: Path = PROJECT_ROOT / "outputs"


def resolve_in_project(*parts: str) -> Path:
    """Resolve a path under the project root."""
    return PROJECT_ROOT.joinpath(*parts)
