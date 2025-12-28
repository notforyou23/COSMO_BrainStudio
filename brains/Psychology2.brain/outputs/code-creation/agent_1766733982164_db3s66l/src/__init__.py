"""src package.

This package hosts the artifact creation success gate implementation and its
CLI entrypoint helpers. Keeping this file minimal ensures imports work in both
local runs and CI without side effects.
"""

from __future__ import annotations

__all__ = ["__version__"]
__version__ = "0.1.0"
