"""Pytest shared fixtures and helpers.

Provides consistent ways to locate the project root, the outputs directory,
and to load/validate JSON artifacts across smoke tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

import pytest
def _find_project_root(start: Path) -> Path:
    """Walk upward from *start* to find a likely project root."""
    markers = ("pyproject.toml", "pytest.ini", "setup.cfg", ".git")
    cur = start.resolve()
    for parent in (cur, *cur.parents):
        if any((parent / m).exists() for m in markers):
            return parent
        # In the Code Interpreter environment, /mnt/data is the effective root.
        if parent.name == "data" and parent.parent.name == "mnt":
            return parent
    return cur
@pytest.fixture(scope="session")
def project_root() -> Path:
    """Session-scoped project root path."""
    return _find_project_root(Path(__file__).parent)
@pytest.fixture(scope="session")
def outputs_dir(project_root: Path) -> Path:
    """Outputs directory used for artifacts/logs; created if missing."""
    out = project_root / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    return out
def load_json(path: Path) -> Any:
    """Load JSON from *path* with a helpful error message."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as e:
        raise AssertionError(f"Expected JSON file to exist: {path}") from e
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Invalid JSON in {path}: {e}") from e
def assert_mapping_has_keys(obj: Any, keys: Iterable[str], *, where: str = "object") -> None:
    """Assert *obj* is a mapping with all required keys."""
    if not isinstance(obj, Mapping):
        raise AssertionError(f"Expected {where} to be a JSON object (mapping), got {type(obj).__name__}")
    missing = [k for k in keys if k not in obj]
    if missing:
        raise AssertionError(f"Missing keys in {where}: {missing}")
def assert_list_of_mappings(obj: Any, *, where: str = "array") -> None:
    """Assert *obj* is a list of JSON objects."""
    if not isinstance(obj, list):
        raise AssertionError(f"Expected {where} to be a JSON array, got {type(obj).__name__}")
    for i, item in enumerate(obj):
        if not isinstance(item, Mapping):
            raise AssertionError(f"Expected {where}[{i}] to be a JSON object, got {type(item).__name__}")
@pytest.fixture()
def json_loader():
    """Fixture returning the load_json helper for convenience."""
    return load_json
@pytest.fixture()
def json_assertions():
    """Fixture exposing lightweight JSON structure assertions."""
    return {
        "has_keys": assert_mapping_has_keys,
        "list_of_mappings": assert_list_of_mappings,
    }
@pytest.fixture(scope="session")
def artifact_path(project_root: Path):
    """Factory to build absolute paths under the project root."""
    def _artifact(rel: str | Path) -> Path:
        return (project_root / Path(rel)).resolve()
    return _artifact
