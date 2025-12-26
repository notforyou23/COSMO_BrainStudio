from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = 1
RESULTS_BASENAME = "results.json"
DEFAULT_OUTPUT_PATH = Path("outputs") / "toy_experiment" / RESULTS_BASENAME


def _fail(msg: str) -> None:
    raise ValueError(f"Invalid toy_experiment results artifact: {msg}")


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _is_finite_number(x: Any) -> bool:
    return _is_number(x) and math.isfinite(float(x))


def _require_mapping(obj: Any, where: str = "root") -> Mapping[str, Any]:
    if not isinstance(obj, Mapping):
        _fail(f"{where} must be an object/dict")
    return obj


def validate_results(data: Any) -> None:
    d = _require_mapping(data, "root")

    sv = d.get("schema_version")
    if sv != SCHEMA_VERSION:
        _fail(f"schema_version must be {SCHEMA_VERSION}")

    if d.get("experiment") != "toy_experiment":
        _fail("experiment must be 'toy_experiment'")

    seed = d.get("seed")
    if not isinstance(seed, int) or isinstance(seed, bool):
        _fail("seed must be an int")

    n = d.get("n_samples")
    if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
        _fail("n_samples must be a positive int")

    samples = d.get("samples")
    if not isinstance(samples, Sequence) or isinstance(samples, (str, bytes, bytearray)):
        _fail("samples must be a list/sequence of numbers")
    if len(samples) != n:
        _fail("samples length must equal n_samples")
    for i, x in enumerate(samples):
        if not _is_finite_number(x):
            _fail(f"samples[{i}] must be a finite number")

    summary = _require_mapping(d.get("summary"), "summary")
    for k in ("mean", "stdev", "min", "max"):
        if k not in summary:
            _fail(f"summary.{k} is required")
        if not _is_finite_number(summary[k]):
            _fail(f"summary.{k} must be a finite number")

    created_at = d.get("created_at")
    if not isinstance(created_at, str) or not created_at.strip():
        _fail("created_at must be a non-empty string")

    extra = d.get("extra")
    if extra is not None and not isinstance(extra, Mapping):
        _fail("extra must be an object/dict when present")


def validate_results_file(path: str | Path) -> dict:
    p = Path(path)
    obj = json.loads(p.read_text(encoding="utf-8"))
    validate_results(obj)
    return obj
