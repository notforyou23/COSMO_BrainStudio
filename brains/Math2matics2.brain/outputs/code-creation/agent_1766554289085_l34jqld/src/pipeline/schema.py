"""Stable schemas + normalization for pipeline artifacts.

This module standardizes keys, types, and ordering for deterministic outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, MutableMapping, Optional, Sequence, Tuple, Union

SCHEMA_VERSION_RESULTS = "results.v1"
SCHEMA_VERSION_RUN_STAMP = "run_stamp.v1"


Json = Union[None, bool, int, float, str, Dict[str, Any], Sequence[Any]]


def _is_num(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _as_str(x: Any, default: str = "") -> str:
    if x is None:
        return default
    return str(x)


def _as_float(x: Any, default: float = 0.0) -> float:
    if _is_num(x):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x.strip())
        except Exception:
            return default
    return default


def _as_int(x: Any, default: int = 0) -> int:
    if isinstance(x, bool):
        return default
    if isinstance(x, int):
        return int(x)
    if isinstance(x, float):
        return int(x)
    if isinstance(x, str):
        try:
            return int(float(x.strip()))
        except Exception:
            return default
    return default


def _as_bool(x: Any, default: bool = False) -> bool:
    if isinstance(x, bool):
        return x
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return bool(x)
    if isinstance(x, str):
        s = x.strip().lower()
        if s in {"true", "1", "yes", "y", "t"}:
            return True
        if s in {"false", "0", "no", "n", "f"}:
            return False
    return default


def _dict(x: Any) -> Dict[str, Any]:
    return dict(x) if isinstance(x, Mapping) else {}


def _list_of_str(x: Any) -> list[str]:
    if x is None:
        return []
    if isinstance(x, (list, tuple)):
        return [str(v) for v in x]
    return [str(x)]


def _stable_sort_dict(d: MutableMapping[str, Any]) -> Dict[str, Any]:
    return {k: d[k] for k in sorted(d.keys())}


def _require_keys(d: Mapping[str, Any], required: Sequence[str], *, ctx: str) -> None:
    missing = [k for k in required if k not in d]
    if missing:
        raise ValueError(f"{ctx} missing required keys: {missing}")


def normalize_results(data: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """Normalize/validate the results artifact dictionary (results.json)."""
    src = _dict(data)
    metrics_in = _dict(src.get("metrics"))
    params_in = _dict(src.get("params"))
    artifacts_in = _dict(src.get("artifacts"))

    metrics = {
        "n": _as_int(metrics_in.get("n"), 0),
        "mean": _as_float(metrics_in.get("mean"), 0.0),
        "std": _as_float(metrics_in.get("std"), 0.0),
        "min": _as_float(metrics_in.get("min"), 0.0),
        "max": _as_float(metrics_in.get("max"), 0.0),
        "sum": _as_float(metrics_in.get("sum"), 0.0),
        "checksum": _as_str(metrics_in.get("checksum"), ""),
    }
    params = {
        "seed": _as_int(params_in.get("seed"), 0),
        "pipeline_version": _as_str(params_in.get("pipeline_version"), ""),
    }
    artifacts = {
        "results_json": _as_str(artifacts_in.get("results_json"), "outputs/results.json"),
        "figure_png": _as_str(artifacts_in.get("figure_png"), "outputs/figure.png"),
        "run_stamp_json": _as_str(artifacts_in.get("run_stamp_json"), "outputs/run_stamp.json"),
        "logs_dir": _as_str(artifacts_in.get("logs_dir"), "outputs/logs"),
    }

    out = {
        "schema_version": SCHEMA_VERSION_RESULTS,
        "status": _as_str(src.get("status"), "ok"),
        "created_utc": _as_str(src.get("created_utc"), ""),
        "metrics": metrics,
        "params": params,
        "artifacts": artifacts,
        "notes": _as_str(src.get("notes"), ""),
    }
    _require_keys(out, ["schema_version", "status", "created_utc", "metrics", "params", "artifacts"], ctx="results")
    out["metrics"] = _stable_sort_dict(out["metrics"])
    out["params"] = _stable_sort_dict(out["params"])
    out["artifacts"] = _stable_sort_dict(out["artifacts"])
    return _stable_sort_dict(out)


def normalize_run_stamp(data: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """Normalize/validate the run stamp artifact dictionary (run_stamp.json)."""
    src = _dict(data)
    env_in = _dict(src.get("environment"))
    inputs_in = _dict(src.get("inputs"))
    outputs_in = _dict(src.get("outputs"))

    environment = {
        "python": _as_str(env_in.get("python"), ""),
        "platform": _as_str(env_in.get("platform"), ""),
        "executable": _as_str(env_in.get("executable"), ""),
    }
    inputs = {
        "seed": _as_int(inputs_in.get("seed"), 0),
        "argv": _list_of_str(inputs_in.get("argv")),
        "workdir": _as_str(inputs_in.get("workdir"), ""),
    }
    outputs = {
        "results_json": _as_str(outputs_in.get("results_json"), "outputs/results.json"),
        "figure_png": _as_str(outputs_in.get("figure_png"), "outputs/figure.png"),
        "run_stamp_json": _as_str(outputs_in.get("run_stamp_json"), "outputs/run_stamp.json"),
        "logs": _list_of_str(outputs_in.get("logs")),
    }

    out = {
        "schema_version": SCHEMA_VERSION_RUN_STAMP,
        "run_id": _as_str(src.get("run_id"), ""),
        "started_utc": _as_str(src.get("started_utc"), ""),
        "finished_utc": _as_str(src.get("finished_utc"), ""),
        "duration_s": _as_float(src.get("duration_s"), 0.0),
        "success": _as_bool(src.get("success"), True),
        "git": _stable_sort_dict(_dict(src.get("git"))),
        "environment": environment,
        "inputs": inputs,
        "outputs": outputs,
    }
    _require_keys(out, ["schema_version", "run_id", "started_utc", "finished_utc", "success", "environment", "inputs", "outputs"], ctx="run_stamp")
    out["environment"] = _stable_sort_dict(out["environment"])
    out["inputs"] = _stable_sort_dict(out["inputs"])
    out["outputs"] = _stable_sort_dict(out["outputs"])
    return _stable_sort_dict(out)
