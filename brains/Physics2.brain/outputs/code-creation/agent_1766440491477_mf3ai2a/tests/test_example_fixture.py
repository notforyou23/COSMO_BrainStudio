from __future__ import annotations

import json
from pathlib import Path

import pytest

from qg_bench.runner import run_benchmark
from qg_bench.validate import iter_validation_issues, validate_file


EXAMPLE_DATASET_PATH = Path("examples/example_dataset.json")

# This is the checked-in expected output for the worked example dataset.
# It intentionally matches the current minimal runner behavior.
EXPECTED_RUNNER_OUTPUT = {
    "dataset_path": "examples/example_dataset.json",
    "n_items": 0,
    "accuracy": 0.0,
    "scores": [],
}


def test_example_dataset_schema_validates() -> None:
    data = validate_file(EXAMPLE_DATASET_PATH)
    issues = list(iter_validation_issues(data))
    assert issues == []


def test_runner_output_matches_expected_fixture(tmp_path: Path) -> None:
    # Run from a relative dataset path so dataset_path in the result is stable.
    result = run_benchmark(EXAMPLE_DATASET_PATH).as_dict()
    assert result == EXPECTED_RUNNER_OUTPUT

    # Optional sanity check: result is JSON-serializable and deterministic.
    out = tmp_path / "out.json"
    out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    assert json.loads(out.read_text(encoding="utf-8")) == EXPECTED_RUNNER_OUTPUT
