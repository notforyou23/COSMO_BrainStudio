from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _schema_path(root: Path) -> Path | None:
    candidates = [
        root / "outputs" / "schemas" / "benchmark_schema.json",
        root / "schemas" / "benchmark_schema.json",
        root / "schema" / "benchmark_schema.json",
        root / "benchmark_schema.json",
        root / "benchmark_schema.schema.json",
    ]
    for p in candidates:
        if p.is_file():
            return p
    # Fallback: first match anywhere under outputs/schemas or schemas.
    for base in [root / "outputs" / "schemas", root / "schemas"]:
        if base.is_dir():
            matches = sorted(base.rglob("*benchmark*schema*.json"))
            if matches:
                return matches[0]
    return None


def _example_json_files(root: Path) -> list[Path]:
    examples_dir = root / "examples"
    if not examples_dir.is_dir():
        return []
    files = sorted(p for p in examples_dir.rglob("*.json") if p.is_file())
    # Exclude any schema files that might be co-located in examples.
    return [p for p in files if "schema" not in p.name.lower()]


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # pragma: no cover
        raise AssertionError(f"Failed to parse JSON: {path}: {e}") from e


@pytest.mark.parametrize("example_path", _example_json_files(_repo_root()))
def test_examples_conform_to_benchmark_input_schema(example_path: Path) -> None:
    root = _repo_root()
    schema_file = _schema_path(root)

    if not (root / "examples").is_dir():
        pytest.skip("No examples/ directory present.")
    if not _example_json_files(root):
        pytest.skip("No example JSON files found under examples/.")

    assert schema_file is not None and schema_file.is_file(), (
        "Example JSON files exist, but benchmark input schema was not found. "
        "Looked for outputs/schemas/benchmark_schema.json (and common alternatives)."
    )

    schema = _load_json(schema_file)
    instance = _load_json(example_path)

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))
    if errors:
        formatted = "\n".join(
            f"- {example_path}: {list(err.absolute_path)}: {err.message}" for err in errors
        )
        raise AssertionError(f"Schema validation failed:\n{formatted}")
