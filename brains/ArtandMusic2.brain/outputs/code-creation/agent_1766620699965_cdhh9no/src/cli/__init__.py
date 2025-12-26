"""
CLI package entry points.

This module provides stable exports for CLI subcommands so the top-level
CLI can integrate them without importing internal modules eagerly.
"""
from __future__ import annotations

from importlib import import_module
from typing import Any, Optional, Tuple
def _load_path_canonicalize_module():
    """
    Lazy-import the path canonicalization command module.

    This avoids import-time side effects and lets the parent CLI import
    src.cli even if optional command dependencies are unavailable.
    """
    return import_module(".path_canonicalize", __package__)
def get_path_canonicalize_exports() -> Tuple[Optional[Any], Optional[Any]]:
    """
    Return (app, register) exports from src.cli.path_canonicalize when available.

    Conventions supported:
      - app: a Typer/Click command/app object (commonly named "app")
      - register: function to attach the command to a parent CLI (commonly named "register")
    """
    try:
        mod = _load_path_canonicalize_module()
    except Exception:
        return None, None

    app = getattr(mod, "app", None)
    register = getattr(mod, "register", None)
    return app, register
__all__ = [
    "get_path_canonicalize_exports",
]
