from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Tuple

import pytest
from jsonschema import Draft202012Validator, ValidationError


def _outputs_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Any:
    import json

    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def schema() -> Mapping[str, Any]:
    schema_path = _outputs_dir() / "schemas" / "benchmark.schema.json"
    return _load_json(schema_path)


def _validate(instance: Any, schema: Mapping[str, Any]) -> None:
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(instance)


def _compute(numbers: List[float]) -> Dict[str, float]:
    total = float(sum(numbers))
    mean = total / float(len(numbers))
    return {"sum": total, "mean": mean}


def _example_artifact(numbers: List[float]) -> Dict[str, Any]:
    computed = _compute(numbers)
    return {
        "schema_version": "1.0.0",
        "case_id": "example_case_001",
        "input": {"numbers": numbers},
        "expected_output": {"sum": computed["sum"], "mean": computed["mean"], "tolerance": 0.0},
        "computed_output": computed,
    }
@pytest.mark.parametrize(
    "numbers",
    [
        [1, 2, 3, 4],
        [0.5, 1.5, 2.5],
        [-1.0, 0.0, 1.0],
    ],
)
def test_example_artifact_conforms_to_schema(schema: Mapping[str, Any], numbers: List[float]) -> None:
    artifact = _example_artifact(numbers)
    _validate(artifact, schema)


def test_schema_rejects_unknown_top_level_keys(schema: Mapping[str, Any]) -> None:
    artifact = _example_artifact([1, 2, 3])
    artifact["unexpected"] = True
    with pytest.raises(ValidationError):
        _validate(artifact, schema)


def test_reference_computation_matches_expected_output(schema: Mapping[str, Any]) -> None:
    artifact = _example_artifact([1.0, 2.0, 3.0, 4.0])
    _validate(artifact, schema)

    tol = float(artifact["expected_output"].get("tolerance", 0.0))
    computed = _compute(list(artifact["input"]["numbers"]))
    assert abs(computed["sum"] - float(artifact["expected_output"]["sum"])) <= tol
    assert abs(computed["mean"] - float(artifact["expected_output"]["mean"])) <= tol
