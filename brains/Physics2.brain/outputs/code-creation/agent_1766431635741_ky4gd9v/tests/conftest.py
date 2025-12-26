"""Shared pytest fixtures and helpers.

These utilities focus on:
- locating the repository root deterministically
- stable JSON read/write (sorted keys, consistent separators, newline)
- normalizing nested structures for deterministic comparisons
"""

from __future__ import annotations

from dataclasses import is_dataclass, asdict
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, MutableMapping, MutableSequence

import pytest
def find_project_root(start: Path) -> Path:
    """Find the repository root by searching upwards for common markers."""
    start = start.resolve()
    markers = ("pyproject.toml", "setup.cfg", "requirements.txt", ".git")
    for p in (start, *start.parents):
        if any((p / m).exists() for m in markers):
            return p
        # fall back: many generated projects include these dirs at root
        if (p / "outputs").is_dir() and (p / "tests").is_dir():
            return p
    return start.parent


@pytest.fixture(scope="session")
def project_root() -> Path:
    return find_project_root(Path(__file__).resolve())
@pytest.fixture(scope="session")
def outputs_dir(project_root: Path) -> Path:
    return project_root / "outputs"


@pytest.fixture(scope="session")
def schemas_dir(outputs_dir: Path) -> Path:
    return outputs_dir / "schemas"


@pytest.fixture(scope="session")
def benchmark_schema_path(schemas_dir: Path) -> Path:
    return schemas_dir / "benchmark_schema.json"


def expected_outputs_dir(outputs_dir: Path) -> Path:
    """Return directory holding committed 'expected' JSON outputs, if present."""
    cand = outputs_dir / "expected"
    return cand if cand.is_dir() else outputs_dir
def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def stable_json_dumps(obj: Any) -> str:
    """Deterministic JSON encoding used for byte-stable comparisons."""
    return json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=False,
        indent=2,
        separators=(",", ": "),
    ) + "\n"


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(stable_json_dumps(obj), encoding="utf-8")
def _normalize_number(x: Any, *, rel_tol: float | None = None, abs_tol: float | None = None, digits: int = 12) -> Any:
    if not isinstance(x, float):
        return x
    # If tolerances are provided, keep full precision; otherwise round for determinism.
    if rel_tol is None and abs_tol is None:
        y = round(x, digits)
        return 0.0 if y == 0.0 else y  # normalize -0.0
    return x


def normalize_for_compare(
    obj: Any,
    *,
    digits: int = 12,
    rel_tol: float | None = None,
    abs_tol: float | None = None,
) -> Any:
    """Recursively normalize structures for deterministic comparisons.

    - dataclasses -> dict
    - dict keys preserved; values normalized
    - lists/tuples preserved order
    - floats optionally rounded (when tolerances are not used)
    """
    if is_dataclass(obj):
        obj = asdict(obj)

    if isinstance(obj, Mapping):
        return {k: normalize_for_compare(v, digits=digits, rel_tol=rel_tol, abs_tol=abs_tol) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [normalize_for_compare(v, digits=digits, rel_tol=rel_tol, abs_tol=abs_tol) for v in obj]
    return _normalize_number(obj, rel_tol=rel_tol, abs_tol=abs_tol, digits=digits)
def iter_json_files(root: Path) -> list[Path]:
    """Return JSON files under root, sorted by relative path."""
    files = [p for p in root.rglob("*.json") if p.is_file()]
    return sorted(files, key=lambda p: p.as_posix())
