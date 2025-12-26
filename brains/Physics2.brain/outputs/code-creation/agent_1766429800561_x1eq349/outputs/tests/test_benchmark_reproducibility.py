from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Mapping

import pytest


def _outputs_dir() -> Path:
    # outputs/tests/... -> outputs/
    return Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_canonical_json(obj: Any) -> str:
    payload = json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _population_variance(xs: List[float], mean: float) -> float:
    return sum((x - mean) ** 2 for x in xs) / float(len(xs))


def _weighted_mean(xs: List[float], ws: List[float]) -> float:
    denom = float(sum(ws))
    if denom == 0.0:
        raise ValueError("sum(weights) must be non-zero")
    return float(sum(w * x for w, x in zip(ws, xs))) / denom


def _compute_result_artifact(case: Mapping[str, Any]) -> Dict[str, Any]:
    series = [float(x) for x in case["inputs"]["series"]]
    weights = [float(w) for w in case["inputs"]["weights"]]
    if len(series) != len(weights):
        raise ValueError("series and weights must have same length")
    if not series:
        raise ValueError("series must be non-empty")

    total = float(sum(series))
    mean = total / float(len(series))
    var = _population_variance(series, mean)
    std = float(math.sqrt(var))
    wmean = _weighted_mean(series, weights)

    return {
        "artifact_type": "benchmark_result",
        "case_id": case["case_id"],
        "checksums": {"series_sha256": _sha256_canonical_json(case["inputs"]["series"])},
        "created_utc": case["created_utc"],
        "inputs": {"series": case["inputs"]["series"], "weights": case["inputs"]["weights"]},
        "name": case["name"],
        "results": {
            "count": len(series),
            "max": float(max(series)),
            "mean": mean,
            "min": float(min(series)),
            "population_stddev": std,
            "population_variance": var,
            "sum": total,
            "weighted_mean": wmean,
        },
        "schema_version": case["schema_version"],
    }


@pytest.mark.parametrize(
    "expected_path",
    [Path("expected") / "benchmark_case_001.expected.json"],
)
def test_benchmark_computation_reproduces_golden_expected_json(expected_path: Path) -> None:
    expected_full_path = _outputs_dir() / expected_path
    expected = _load_json(expected_full_path)

    computed = _compute_result_artifact(expected)

    # Exact structural equality: keys/values must match the committed golden file.
    assert computed == expected
