"""minipipeline: a tiny, deterministic pipeline that writes run artifacts.

Public API:
- run(payload=None, outputs_dir=None) -> dict
"""

from __future__ import annotations

from .run import run

__all__ = ["run"]
