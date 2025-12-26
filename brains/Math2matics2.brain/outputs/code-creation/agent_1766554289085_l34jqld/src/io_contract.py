from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple, Union
import json
import math
import datetime as _dt

CONTRACT_NAME = "cosmo.toy_experiment.results"
CONTRACT_VERSION = "1.0.0"


JsonScalar = Union[str, int, float, bool, None]
Json = Union[JsonScalar, Dict[str, Any], list]


class ContractError(ValueError):
    """Raised when results.json does not satisfy the fixed output contract."""


def utc_now_iso() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not (isinstance(x, float) and (math.isnan(x) or math.isinf(x)))


def _req(obj: Mapping[str, Any], key: str, typ: Union[type, Tuple[type, ...]]) -> Any:
    if key not in obj:
        raise ContractError(f"Missing required key: {key}")
    val = obj[key]
    if not isinstance(val, typ):
        raise ContractError(f"Key '{key}' has wrong type: expected {typ}, got {type(val)}")
    return val


def _req_number(obj: Mapping[str, Any], key: str) -> float:
    if key not in obj:
        raise ContractError(f"Missing required key: {key}")
    val = obj[key]
    if not _is_number(val):
        raise ContractError(f"Key '{key}' must be a finite number, got {val!r}")
    return float(val)


def _req_optional_str(obj: Mapping[str, Any], key: str) -> Optional[str]:
    if key not in obj or obj[key] is None:
        return None
    if not isinstance(obj[key], str):
        raise ContractError(f"Key '{key}' must be a string or null, got {type(obj[key])}")
    return obj[key]


def validate_results(results: Mapping[str, Any]) -> None:
    """Validate outputs/results.json against the fixed contract.

    Required top-level keys:
      - contract: {name:str, version:str}
      - created_utc: str (RFC3339 / ISO-8601 with 'Z' preferred)
      - seed: int
      - paths: {results_json:str, figure_png:str}
      - experiment: {name:str}
      - metrics: {true_location:number, sample_mean:{...}, median_of_means:{...}}
    """
    if not isinstance(results, Mapping):
        raise ContractError(f"Results must be an object/dict, got {type(results)}")

    contract = _req(results, "contract", Mapping)
    if _req(contract, "name", str) != CONTRACT_NAME:
        raise ContractError(f"contract.name must be '{CONTRACT_NAME}'")
    if _req(contract, "version", str) != CONTRACT_VERSION:
        raise ContractError(f"contract.version must be '{CONTRACT_VERSION}'")

    _req(results, "created_utc", str)
    seed = _req(results, "seed", int)
    if seed < 0:
        raise ContractError("seed must be non-negative")

    paths = _req(results, "paths", Mapping)
    _req(paths, "results_json", str)
    _req(paths, "figure_png", str)

    env = _req(results, "environment", Mapping)
    _req_optional_str(env, "python")
    _req_optional_str(env, "platform")
    _req_optional_str(env, "numpy")
    _req_optional_str(env, "matplotlib")

    exp = _req(results, "experiment", Mapping)
    _req(exp, "name", str)
    _req_optional_str(exp, "description")

    metrics = _req(results, "metrics", Mapping)
    _req_number(metrics, "true_location")

    def _validate_est(est: Mapping[str, Any], label: str) -> None:
        _req(est, "name", str)
        _req_number(est, "estimate")
        _req_number(est, "abs_error")
        _req_number(est, "signed_error")
        if "details" in est:
            if not isinstance(est["details"], Mapping):
                raise ContractError(f"metrics.{label}.details must be an object if present")

    _validate_est(_req(metrics, "sample_mean", Mapping), "sample_mean")
    _validate_est(_req(metrics, "median_of_means", Mapping), "median_of_means")


def dumps_canonical(obj: Json, *, indent: int = 2) -> str:
    return json.dumps(obj, indent=indent, sort_keys=True, ensure_ascii=False) + "\n"


def write_results(results_path: Union[str, Path], results: Mapping[str, Any], *, indent: int = 2) -> Path:
    """Validate and write results.json deterministically (sorted keys, fixed indent)."""
    validate_results(results)
    p = Path(results_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(dumps_canonical(results, indent=indent), encoding="utf-8")
    return p


def build_minimal_results(*, seed: int, results_json: str, figure_png: str, experiment_name: str) -> Dict[str, Any]:
    """Create a minimal valid results payload; callers should fill in metrics."""
    return {
        "contract": {"name": CONTRACT_NAME, "version": CONTRACT_VERSION},
        "created_utc": utc_now_iso(),
        "seed": int(seed),
        "paths": {"results_json": str(results_json), "figure_png": str(figure_png)},
        "environment": {"python": None, "platform": None, "numpy": None, "matplotlib": None},
        "experiment": {"name": str(experiment_name), "description": None},
        "metrics": {
            "true_location": 0.0,
            "sample_mean": {"name": "sample_mean", "estimate": 0.0, "abs_error": 0.0, "signed_error": 0.0, "details": {}},
            "median_of_means": {"name": "median_of_means", "estimate": 0.0, "abs_error": 0.0, "signed_error": 0.0, "details": {}},
        },
    }
