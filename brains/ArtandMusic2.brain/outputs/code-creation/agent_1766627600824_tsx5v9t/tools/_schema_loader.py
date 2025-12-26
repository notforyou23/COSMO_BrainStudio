"""Shared utilities for locating, loading, and caching the authoritative case-study schema.

This module centralizes the selection of ONE blessed schema file:
schemas/METADATA_SCHEMA.json (relative to repository root).

Public API:
- schema_path() -> Path
- load_schema() -> dict
- schema_id() -> str | None
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional
_SCHEMA_ENV = "COSMO_METADATA_SCHEMA_PATH"
_SCHEMA_RELATIVE = Path("schemas") / "METADATA_SCHEMA.json"


def _repo_root_from(start: Path) -> Path:
    """Find the repository root by searching upward for 'schemas/METADATA_SCHEMA.json'."""
    start = start.resolve()
    for parent in (start, *start.parents):
        candidate = parent / _SCHEMA_RELATIVE
        if candidate.is_file():
            return parent
    raise FileNotFoundError(
        f"Authoritative schema not found; expected '{_SCHEMA_RELATIVE.as_posix()}' above {start}"
    )
def schema_path() -> Path:
    """Return the resolved Path to the authoritative METADATA_SCHEMA.json.

    Resolution order:
      1) COSMO_METADATA_SCHEMA_PATH env var (if set)
      2) nearest ancestor containing schemas/METADATA_SCHEMA.json
    """
    override = os.environ.get(_SCHEMA_ENV, "").strip()
    if override:
        p = Path(override).expanduser()
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        if not p.is_file():
            raise FileNotFoundError(f"{_SCHEMA_ENV} points to missing file: {p}")
        return p

    root = _repo_root_from(Path(__file__).parent)
    return (root / _SCHEMA_RELATIVE).resolve()
@lru_cache(maxsize=1)
def load_schema() -> Dict[str, Any]:
    """Load and return the authoritative JSON Schema as a dictionary (cached)."""
    path = schema_path()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise OSError(f"Failed reading schema at {path}: {e}") from e

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in schema at {path}: {e}") from e

    if not isinstance(data, dict):
        raise ValueError(f"Schema root must be an object; got {type(data).__name__} in {path}")
    return data


def schema_id() -> Optional[str]:
    """Return $id from the loaded schema if present."""
    return load_schema().get("$id")


def clear_schema_cache() -> None:
    """Clear the cached schema (useful for tests)."""
    load_schema.cache_clear()
