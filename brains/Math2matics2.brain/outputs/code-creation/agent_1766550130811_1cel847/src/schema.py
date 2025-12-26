from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union
import math
import json
from pathlib import Path

Json = Union[None, bool, int, float, str, List["Json"], Dict[str, "Json"]]

SCHEMA_VERSION = "1.0"
RESULTS_JSON_REL = "outputs/results.json"
FIGURE_PNG_REL = "outputs/figure.png"

TOP_LEVEL_KEYS: Tuple[str, ...] = (
    "schema_version",
    "artifacts",
    "run",
    "data",
    "parameters",
    "metrics",
)

ARTIFACT_KEYS: Tuple[str, ...] = ("results_json", "figure_png")
RUN_KEYS: Tuple[str, ...] = ("seed", "started_utc", "finished_utc", "versions")
VERSIONS_KEYS: Tuple[str, ...] = ("python", "numpy", "matplotlib")
DATA_KEYS: Tuple[str, ...] = ("n", "x_mean", "y_mean", "x_std", "y_std")
PARAM_KEYS: Tuple[str, ...] = ("slope", "intercept")
METRIC_KEYS: Tuple[str, ...] = ("mse", "r2")

NUMERIC_FIELDS: Tuple[Tuple[Tuple[str, ...], type], ...] = (
    (("data", "n"), int),
    (("data", "x_mean"), (int, float)),
    (("data", "y_mean"), (int, float)),
    (("data", "x_std"), (int, float)),
    (("data", "y_std"), (int, float)),
    (("parameters", "slope"), (int, float)),
    (("parameters", "intercept"), (int, float)),
    (("metrics", "mse"), (int, float)),
    (("metrics", "r2"), (int, float)),
)

DEFAULT_TOLERANCES: Dict[Tuple[str, ...], Tuple[float, float]] = {
    ("metrics", "mse"): (1e-12, 1e-9),
    ("metrics", "r2"): (1e-12, 1e-9),
    ("parameters", "slope"): (1e-12, 1e-9),
    ("parameters", "intercept"): (1e-12, 1e-9),
    ("data", "x_mean"): (1e-12, 1e-9),
    ("data", "y_mean"): (1e-12, 1e-9),
    ("data", "x_std"): (1e-12, 1e-9),
    ("data", "y_std"): (1e-12, 1e-9),
}


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(float(x))


def _require_keys_exact(obj: Mapping[str, Any], expected: Sequence[str], where: str) -> List[str]:
    errs: List[str] = []
    got = set(obj.keys())
    exp = set(expected)
    missing = sorted(exp - got)
    extra = sorted(got - exp)
    if missing:
        errs.append(f"{where}: missing keys {missing}")
    if extra:
        errs.append(f"{where}: unexpected keys {extra}")
    return errs


def _get_path(obj: Mapping[str, Any], path: Sequence[str]) -> Any:
    cur: Any = obj
    for p in path:
        if not isinstance(cur, Mapping) or p not in cur:
            raise KeyError(".".join(path))
        cur = cur[p]
    return cur


def assert_close(actual: float, expected: float, *, atol: float = 0.0, rtol: float = 0.0, name: str = "value") -> None:
    if not (_is_number(actual) and _is_number(expected)):
        raise AssertionError(f"{name}: non-finite numeric comparison (actual={actual!r}, expected={expected!r})")
    if not math.isclose(float(actual), float(expected), rel_tol=float(rtol), abs_tol=float(atol)):
        raise AssertionError(f"{name}: {actual} != {expected} within atol={atol}, rtol={rtol}")


def validate_results_doc(doc: Mapping[str, Any], *, strict_keys: bool = True) -> None:
    errs: List[str] = []
    if not isinstance(doc, Mapping):
        raise ValueError("results must be a JSON object")

    if strict_keys:
        errs += _require_keys_exact(doc, TOP_LEVEL_KEYS, "root")

    if doc.get("schema_version") != SCHEMA_VERSION:
        errs.append(f"schema_version: expected {SCHEMA_VERSION!r}, got {doc.get('schema_version')!r}")

    artifacts = doc.get("artifacts")
    if not isinstance(artifacts, Mapping):
        errs.append("artifacts: must be an object")
    else:
        if strict_keys:
            errs += _require_keys_exact(artifacts, ARTIFACT_KEYS, "artifacts")
        if artifacts.get("results_json") != RESULTS_JSON_REL:
            errs.append(f"artifacts.results_json: expected {RESULTS_JSON_REL!r}")
        if artifacts.get("figure_png") != FIGURE_PNG_REL:
            errs.append(f"artifacts.figure_png: expected {FIGURE_PNG_REL!r}")

    run = doc.get("run")
    if not isinstance(run, Mapping):
        errs.append("run: must be an object")
    else:
        if strict_keys:
            errs += _require_keys_exact(run, RUN_KEYS, "run")
        if not isinstance(run.get("seed"), int) or isinstance(run.get("seed"), bool):
            errs.append("run.seed: must be an int")
        for k in ("started_utc", "finished_utc"):
            if not isinstance(run.get(k), str) or not run.get(k):
                errs.append(f"run.{k}: must be a non-empty string")
        versions = run.get("versions")
        if not isinstance(versions, Mapping):
            errs.append("run.versions: must be an object")
        else:
            if strict_keys:
                errs += _require_keys_exact(versions, VERSIONS_KEYS, "run.versions")
            for k in VERSIONS_KEYS:
                if not isinstance(versions.get(k), str) or not versions.get(k):
                    errs.append(f"run.versions.{k}: must be a non-empty string")

    for section, keys, where in (
        ("data", DATA_KEYS, "data"),
        ("parameters", PARAM_KEYS, "parameters"),
        ("metrics", METRIC_KEYS, "metrics"),
    ):
        obj = doc.get(section)
        if not isinstance(obj, Mapping):
            errs.append(f"{where}: must be an object")
            continue
        if strict_keys:
            errs += _require_keys_exact(obj, keys, where)

    # Type + finiteness checks for numeric fields
    for path, tp in NUMERIC_FIELDS:
        try:
            v = _get_path(doc, path)
        except KeyError:
            continue
        if not isinstance(v, tp) or isinstance(v, bool):
            errs.append(f"{'.'.join(path)}: expected {tp}, got {type(v).__name__}")
            continue
        if isinstance(v, float) and not math.isfinite(v):
            errs.append(f"{'.'.join(path)}: must be finite")

    # Metric sanity
    try:
        r2 = float(_get_path(doc, ("metrics", "r2")))
        if not (-1.0 <= r2 <= 1.0):
            errs.append("metrics.r2: expected within [-1, 1]")
    except Exception:
        pass
    try:
        mse = float(_get_path(doc, ("metrics", "mse")))
        if mse < 0.0:
            errs.append("metrics.mse: expected >= 0")
    except Exception:
        pass

    if errs:
        raise ValueError("Artifact validation failed:\n- " + "\n- ".join(errs))


def validate_results_path(path: Union[str, Path], *, strict_keys: bool = True) -> Dict[str, Any]:
    p = Path(path)
    doc = json.loads(p.read_text(encoding="utf-8"))
    validate_results_doc(doc, strict_keys=strict_keys)
    return doc


def expected_keys() -> Dict[str, Tuple[str, ...]]:
    return {
        "root": TOP_LEVEL_KEYS,
        "artifacts": ARTIFACT_KEYS,
        "run": RUN_KEYS,
        "run.versions": VERSIONS_KEYS,
        "data": DATA_KEYS,
        "parameters": PARAM_KEYS,
        "metrics": METRIC_KEYS,
    }


def numeric_tolerances(overrides: Optional[Dict[Tuple[str, ...], Tuple[float, float]]] = None) -> Dict[Tuple[str, ...], Tuple[float, float]]:
    out = dict(DEFAULT_TOLERANCES)
    if overrides:
        out.update(overrides)
    return out
