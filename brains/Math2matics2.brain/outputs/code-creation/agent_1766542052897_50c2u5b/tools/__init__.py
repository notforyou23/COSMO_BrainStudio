"""Project tooling package.

This package hosts helper scripts/modules used by the artifact output promotion
workflow (e.g., copying agent-scoped artifacts into the canonical /outputs/
directory and generating outputs/index.md).

Keeping this file present makes imports like `from tools import promote_artifacts`
reliable when the repository is executed in different contexts (tests, CI, or
direct CLI runs).
"""

from __future__ import annotations

__all__: list[str] = []
