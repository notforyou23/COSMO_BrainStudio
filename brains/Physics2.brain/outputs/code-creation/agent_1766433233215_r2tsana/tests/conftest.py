from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Iterable

import pytest
def _repo_root() -> Path:
    # tests/ -> repo root
    return Path(__file__).resolve().parents[1]


def _first_existing(paths: Iterable[Path]) -> Path | None:
    for p in paths:
        if p.is_file():
            return p
    return None


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # pragma: no cover
        raise AssertionError(f"Failed to parse JSON: {path}: {e}") from e
@pytest.fixture(scope="session")
def repo_root() -> Path:
    return _repo_root()


@pytest.fixture(scope="session")
def examples_dir(repo_root: Path) -> Path:
    return repo_root / "examples"


@pytest.fixture(scope="session")
def schema_path(repo_root: Path) -> Path:
    candidates = [
        repo_root / "outputs" / "schemas" / "benchmark_schema.json",
        repo_root / "schemas" / "benchmark_schema.json",
        repo_root / "schema" / "benchmark_schema.json",
        repo_root / "benchmark_schema.json",
        repo_root / "benchmark_schema.schema.json",
    ]
    found = _first_existing(candidates)
    if found is not None:
        return found
    # Fallback: search common schema directories.
    for base in [repo_root / "outputs" / "schemas", repo_root / "schemas", repo_root]:
        if base.is_dir():
            matches = sorted(base.rglob("*benchmark*schema*.json"))
            if matches:
                return matches[0]
    raise FileNotFoundError(
        "Benchmark input schema JSON not found. "
        "Expected e.g. outputs/schemas/benchmark_schema.json."
    )
@pytest.fixture(scope="session")
def json_load() -> Callable[[Path], Any]:
    return _load_json


@pytest.fixture(scope="session")
def tolerances() -> dict[str, float]:
    # Configure via env for CI/local tweaking.
    atol = float(os.environ.get("ATOL", "1e-6"))
    rtol = float(os.environ.get("RTOL", "1e-6"))
    return {"atol": atol, "rtol": rtol}
@pytest.fixture(scope="session")
def output_root(repo_root: Path) -> Path:
    # Deterministic output location for both local runs and CI artifacts upload.
    # CI can override via CI_OUTPUT_DIR.
    out = Path(os.environ.get("CI_OUTPUT_DIR", repo_root / "tests" / "ci_outputs"))
    out.mkdir(parents=True, exist_ok=True)
    return out


@pytest.fixture()
def run_output_dir(output_root: Path, request: pytest.FixtureRequest) -> Path:
    # Per-test directory (stable name, easy to upload/inspect).
    name = request.node.name.replace(os.sep, "_")
    p = output_root / name
    p.mkdir(parents=True, exist_ok=True)
    return p
@pytest.fixture(scope="session")
def benchmark_case_001_input(repo_root: Path) -> Path | None:
    candidates = [
        repo_root / "examples" / "benchmark_case_001.json",
        repo_root / "examples" / "benchmark_case_001" / "input.json",
    ]
    found = _first_existing(candidates)
    if found is not None:
        return found
    hits = sorted(
        p for p in repo_root.rglob("benchmark_case_001*.json")
        if "expected" not in p.name.lower()
    )
    return hits[0] if hits else None


@pytest.fixture(scope="session")
def benchmark_case_001_expected(repo_root: Path) -> list[Path]:
    hits = sorted(
        p for p in repo_root.rglob("benchmark_case_001*expected*.json")
        if p.is_file()
    )
    if hits:
        return hits
    expected_dir = repo_root / "outputs" / "expected"
    if expected_dir.is_dir():
        return sorted(expected_dir.rglob("benchmark_case_001*.json"))
    return []
