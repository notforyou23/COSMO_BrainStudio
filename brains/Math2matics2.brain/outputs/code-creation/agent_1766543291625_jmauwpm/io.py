"""Backwards-compatible shim for legacy imports.

This project refactored experiment I/O utilities into the reusable package
``src.experiments.io``. Importing from the top-level ``io`` module is
deprecated and will be removed in a future version.

Use:
    from src.experiments.io import ...

This shim re-exports the public API to keep older code working while emitting
deprecation guidance.
"""

from __future__ import annotations

import warnings
from importlib import import_module
from types import ModuleType
from typing import Any, List

_DEPRECATION_MESSAGE = (
    "Importing experiment IO utilities from 'io' is deprecated. "
    "Please update imports to 'from src.experiments.io import ...' (or "
    "'import src.experiments.io as exp_io'). This shim will be removed in a "
    "future release."
)

warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)

_io: ModuleType = import_module("src.experiments.io")
def __getattr__(name: str) -> Any:
    """Forward attribute access to ``src.experiments.io``."""
    try:
        return getattr(_io, name)
    except AttributeError as e:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from e


def __dir__() -> List[str]:
    """Expose a merged directory listing for IDEs and introspection."""
    public = set(getattr(_io, "__all__", [])) or {n for n in dir(_io) if not n.startswith("_")}
    return sorted(set(globals().keys()) | public)
# Re-export public names eagerly for common star-import / help() use-cases.
__all__ = list(getattr(_io, "__all__", [])) or [n for n in dir(_io) if not n.startswith("_")]

for _name in __all__:
    # Avoid overriding shim-specific globals.
    if _name not in globals():
        globals()[_name] = getattr(_io, _name)
