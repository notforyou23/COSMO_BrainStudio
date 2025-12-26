from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Tuple
import json
import math


SCHEMA_VERSION = "1.0"
REQUIRED_TOP_LEVEL_KEYS = (
    "schema_version",
    "status",
    "seed",
    "metrics",
    "artifacts",
)
OPTIONAL_TOP_LEVEL_KEYS = (
    "run_id",
    "created_at",
    "notes",
    "warnings",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _is_json_number(x: Any) -> bool:
    if isinstance(x, bool) or x is None:
        return False
    if isinstance(x, int):
        return True
    if isinstance(x, float):
        return math.isfinite(x)
    return False


def _validate_jsonable(value: Any, path: str, errors: List[str]) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            errors.append(f"{path}: float must be finite (not NaN/inf).")
        return
    if isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            _validate_jsonable(v, f"{path}[{i}]", errors)
        return
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                errors.append(f"{path}: dict keys must be strings (got {type(k).__name__}).")
                continue
            _validate_jsonable(v, f"{path}.{k}" if path else k, errors)
        return
    errors.append(f"{path}: unsupported JSON type {type(value).__name__}.")


def validate_results(data: Mapping[str, Any]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    if not isinstance(data, Mapping):
        return False, ["Root must be an object/dict."]

    for k in REQUIRED_TOP_LEVEL_KEYS:
        if k not in data:
            errors.append(f"Missing required key: {k}")

    for k in data.keys():
        if k not in REQUIRED_TOP_LEVEL_KEYS and k not in OPTIONAL_TOP_LEVEL_KEYS:
            errors.append(f"Unexpected top-level key: {k}")

    sv = data.get("schema_version")
    if sv != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION!r} (got {sv!r}).")

    status = data.get("status")
    if status not in ("ok", "error"):
        errors.append("status must be one of: 'ok', 'error'.")

    seed = data.get("seed")
    if seed is not None and not isinstance(seed, int):
        errors.append("seed must be an integer or null.")

    run_id = data.get("run_id")
    if run_id is not None and not isinstance(run_id, str):
        errors.append("run_id must be a string if provided.")

    created_at = data.get("created_at")
    if created_at is not None and not isinstance(created_at, str):
        errors.append("created_at must be an ISO-8601 string if provided.")

    notes = data.get("notes")
    if notes is not None and not isinstance(notes, str):
        errors.append("notes must be a string if provided.")

    warnings = data.get("warnings")
    if warnings is not None:
        if not isinstance(warnings, list) or any(not isinstance(x, str) for x in warnings):
            errors.append("warnings must be a list of strings if provided.")

    metrics = data.get("metrics")
    if metrics is None:
        pass
    elif not isinstance(metrics, Mapping):
        errors.append("metrics must be an object/dict.")
    else:
        for mk, mv in metrics.items():
            if not isinstance(mk, str):
                errors.append("metrics keys must be strings.")
                continue
            if not _is_json_number(mv):
                errors.append(f"metrics.{mk}: must be a finite number.")

    artifacts = data.get("artifacts")
    if artifacts is None:
        pass
    elif not isinstance(artifacts, Mapping):
        errors.append("artifacts must be an object/dict.")
    else:
        fig = artifacts.get("figure_png")
        if fig is not None and not isinstance(fig, str):
            errors.append("artifacts.figure_png must be a string path if provided.")
        results = artifacts.get("results_json")
        if results is not None and not isinstance(results, str):
            errors.append("artifacts.results_json must be a string path if provided.")

    _validate_jsonable(data, "", errors)
    return (len(errors) == 0), errors


def assert_valid_results(data: Mapping[str, Any]) -> None:
    ok, errors = validate_results(data)
    if not ok:
        msg = "Invalid results schema:\n" + "\n".join(f"- {e}" for e in errors)
        raise ValueError(msg)


def normalize_results(data: MutableMapping[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    out["schema_version"] = data.get("schema_version", SCHEMA_VERSION)
    out["status"] = data.get("status", "ok")
    out["seed"] = data.get("seed", None)
    out["metrics"] = dict(data.get("metrics") or {})
    out["artifacts"] = dict(data.get("artifacts") or {})
    if "run_id" in data and data["run_id"] is not None:
        out["run_id"] = data["run_id"]
    out["created_at"] = data.get("created_at") or utc_now_iso()
    if "notes" in data and data["notes"] is not None:
        out["notes"] = data["notes"]
    if "warnings" in data and data["warnings"] is not None:
        out["warnings"] = list(data["warnings"])
    assert_valid_results(out)
    return out


def write_results_json(path: Path, results: Mapping[str, Any]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = normalize_results(dict(results))
    text = json.dumps(
        normalized,
        sort_keys=True,
        indent=2,
        ensure_ascii=False,
        separators=(",", ": "),
    )
    path.write_text(text + "\n", encoding="utf-8")
    return path
