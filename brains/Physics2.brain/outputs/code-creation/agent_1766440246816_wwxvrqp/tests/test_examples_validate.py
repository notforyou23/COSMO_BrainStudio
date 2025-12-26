from __future__ import annotations

import json
from pathlib import Path

import pytest


def _repo_root() -> Path:
    # tests/ -> repo root
    return Path(__file__).resolve().parents[1]


def _schema_path() -> Path:
    return _repo_root() / "schemas" / "benchmark.schema.json"


def _example_paths() -> list[Path]:
    root = _repo_root()
    candidates = []
    for pattern in ("outputs/examples/*.json", "examples/*.json"):
        candidates.extend(sorted(root.glob(pattern)))
    # De-duplicate while preserving order
    seen: set[Path] = set()
    out: list[Path] = []
    for p in candidates:
        if p not in seen and p.is_file():
            out.append(p)
            seen.add(p)
    return out


@pytest.mark.parametrize("example_path", _example_paths())
def test_examples_are_valid_json(example_path: Path) -> None:
    # This test is intentionally schema-agnostic: it ensures examples stay parseable.
    with example_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict), "Example root must be a JSON object"


@pytest.mark.parametrize("example_path", _example_paths())
def test_examples_conform_to_benchmark_schema(example_path: Path) -> None:
    schema_path = _schema_path()
    if not schema_path.exists():
        pytest.skip("Schema not present at schemas/benchmark.schema.json")

    try:
        import jsonschema
    except Exception as e:  # pragma: no cover
        pytest.skip(f"jsonschema not available: {e}")

    with schema_path.open("r", encoding="utf-8") as f:
        schema = json.load(f)

    with example_path.open("r", encoding="utf-8") as f:
        instance = json.load(f)

    Validator = jsonschema.validators.validator_for(schema)
    Validator.check_schema(schema)
    Validator(schema).validate(instance)
