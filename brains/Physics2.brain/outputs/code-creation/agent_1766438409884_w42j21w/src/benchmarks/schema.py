"""Schema loader for the benchmark JSON Schema.

This module is responsible for locating the repository's schema files (under the
top-level ``schema/`` directory), loading the root schema as a Python ``dict``,
and configuring local reference resolution so that ``$ref`` works across files.

The primary entry point is :func:`load_schema`.
"""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple, Union
from urllib.parse import urlparse

try:
    # jsonschema < 4.18: present and commonly used
    from jsonschema import RefResolver  # type: ignore
except Exception:  # pragma: no cover
    RefResolver = None  # type: ignore
def _repo_root() -> Path:
    """Return the repository root (parent of ``src/``).

    Assumes this file lives at ``<root>/src/benchmarks/schema.py``.
    """
    return Path(__file__).resolve().parents[2]


def _schema_dir() -> Path:
    return _repo_root() / "schema"


def _pick_root_schema(schema_dir: Path) -> Path:
    """Heuristically pick a root schema JSON file.

    Preference order is a small list of common names; otherwise we fall back to
    the first ``*.schema.json`` / ``*.json`` file in the directory.
    """
    candidates = [
        schema_dir / "benchmark.schema.json",
        schema_dir / "benchmark-run.schema.json",
        schema_dir / "run.schema.json",
        schema_dir / "schema.json",
    ]
    for p in candidates:
        if p.is_file():
            return p
    for pat in ("*.schema.json", "*.json"):
        hits = sorted(schema_dir.glob(pat))
        if hits:
            return hits[0]
    raise FileNotFoundError(
        f"No schema JSON files found in {schema_dir}. Expected e.g. benchmark.schema.json"
    )
def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _file_handler(uri: str) -> Any:
    """Load a referenced schema from disk for the ``file://`` scheme."""
    parsed = urlparse(uri)
    # urlparse("file:///...").path is percent-decoded on most platforms.
    path = Path(parsed.path)
    return _load_json(path)


def _make_resolver(schema: Mapping[str, Any], *, base_uri: str):
    """Create a local-only resolver compatible with ``jsonschema``.

    Returns ``None`` if the installed jsonschema no longer exposes RefResolver.
    """
    if RefResolver is None:  # pragma: no cover
        return None
    return RefResolver(base_uri=base_uri, referrer=schema, handlers={"file": _file_handler})
@lru_cache(maxsize=1)
def load_schema(
    *,
    schema_path: Optional[Union[str, Path]] = None,
    return_resolver: bool = False,
) -> Union[Dict[str, Any], Tuple[Dict[str, Any], Any]]:
    """Load the benchmark JSON Schema.

    Parameters
    ----------
    schema_path:
        Optional explicit path to the root schema JSON. If omitted, the loader
        looks under ``<repo-root>/schema``.
    return_resolver:
        If True, return ``(schema, resolver)`` where ``resolver`` can be passed
        to ``jsonschema`` validators to resolve local ``$ref``.

    Notes
    -----
    The schema dictionary is returned unchanged; callers are expected to pass
    the returned resolver when constructing a validator.
    """
    if schema_path is None:
        schema_dir = _schema_dir()
        schema_file = _pick_root_schema(schema_dir)
    else:
        schema_file = Path(schema_path).expanduser().resolve()
        if schema_file.is_dir():
            schema_file = _pick_root_schema(schema_file)

    schema = _load_json(schema_file)
    base_uri = schema_file.resolve().as_uri()
    resolver = _make_resolver(schema, base_uri=base_uri)

    return (schema, resolver) if return_resolver else schema
