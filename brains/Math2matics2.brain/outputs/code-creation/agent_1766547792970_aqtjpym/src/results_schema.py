from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple, Union
import platform
import sys

SCHEMA_VERSION = "1"
RESULTS_FILENAME = "results.json"

JSONScalar = Union[str, int, float, bool, None]
JSONValue = Union[JSONScalar, Dict[str, "JSONValue"], List["JSONValue"]]

# Lightweight, stable schema (versioned) for outputs/results.json.
# This module intentionally avoids heavy dependencies; validation is implemented here.
SCHEMA_V1: Dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "required_top_level": ["schema_version", "generated_at", "run", "metrics", "figures", "artifacts"],
    "run_required": ["id", "seed", "python", "platform"],
    "figure_required": ["path", "sha256"],
}
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _is_json_scalar(x: Any) -> bool:
    return x is None or isinstance(x, (str, int, float, bool))


def coerce_json(x: Any) -> JSONValue:
    # Handle common numeric scalar types (numpy, torch) without importing them.
    if _is_json_scalar(x):
        return x  # type: ignore[return-value]
    if hasattr(x, "item") and callable(getattr(x, "item")):
        try:
            v = x.item()
            if _is_json_scalar(v):
                return v  # type: ignore[return-value]
        except Exception:
            pass
    if isinstance(x, Mapping):
        return {str(k): coerce_json(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [coerce_json(v) for v in x]
    if isinstance(x, Path):
        return str(x)
    # Last resort: stable string representation.
    return str(x)


def _fail(msg: str, path: str = "$") -> None:
    raise ValueError(f"{msg} at {path}")


def _require_key(d: Mapping[str, Any], key: str, path: str) -> Any:
    if key not in d:
        _fail("Missing required field", f"{path}.{key}")
    return d[key]


def _require_type(v: Any, typ: Union[type, Tuple[type, ...]], path: str) -> None:
    if not isinstance(v, typ):
        _fail(f"Expected {typ} got {type(v)}", path)
def validate_results_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, Mapping):
        _fail("Payload must be an object", "$")
    p = dict(payload)

    for k in SCHEMA_V1["required_top_level"]:
        _require_key(p, k, "$")

    if str(p.get("schema_version")) != SCHEMA_VERSION:
        _fail(f"Unsupported schema_version {p.get('schema_version')!r}", "$.schema_version")

    _require_type(p["generated_at"], str, "$.generated_at")

    run = _require_key(p, "run", "$")
    _require_type(run, Mapping, "$.run")
    run = dict(run)
    for k in SCHEMA_V1["run_required"]:
        _require_key(run, k, "$.run")
    _require_type(run["id"], str, "$.run.id")
    if not isinstance(run["seed"], int):
        # allow numeric strings -> int coercion if safe
        try:
            run["seed"] = int(run["seed"])
        except Exception:
            _fail("seed must be int", "$.run.seed")
    _require_type(run["python"], str, "$.run.python")
    _require_type(run["platform"], str, "$.run.platform")
    p["run"] = run

    metrics = _require_key(p, "metrics", "$")
    _require_type(metrics, Mapping, "$.metrics")
    p["metrics"] = coerce_json(metrics)

    figs = _require_key(p, "figures", "$")
    if not isinstance(figs, list):
        _fail("figures must be a list", "$.figures")
    out_figs: List[Dict[str, Any]] = []
    for i, f in enumerate(figs):
        if not isinstance(f, Mapping):
            _fail("figure must be an object", f"$.figures[{i}]")
        fd = dict(f)
        for k in SCHEMA_V1["figure_required"]:
            _require_key(fd, k, f"$.figures[{i}]")
        _require_type(fd["path"], str, f"$.figures[{i}].path")
        _require_type(fd["sha256"], str, f"$.figures[{i}].sha256")
        if "title" in fd and fd["title"] is not None:
            _require_type(fd["title"], str, f"$.figures[{i}].title")
        out_figs.append(fd)
    p["figures"] = out_figs

    artifacts = _require_key(p, "artifacts", "$")
    _require_type(artifacts, Mapping, "$.artifacts")
    p["artifacts"] = coerce_json(artifacts)

    # Optional standardized fields
    if "notes" in p and p["notes"] is not None:
        _require_type(p["notes"], str, "$.notes")
    if "content_hashes" in p:
        p["content_hashes"] = coerce_json(p["content_hashes"])

    return p
def sha256_file(path: Union[str, Path], chunk_size: int = 1024 * 1024) -> str:
    p = Path(path)
    h = sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def default_run_metadata(*, run_id: str, seed: int, command: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    return {
        "id": str(run_id),
        "seed": int(seed),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "argv": list(command) if command is not None else list(sys.argv),
    }


def build_results_payload(
    *,
    run: Mapping[str, Any],
    metrics: Mapping[str, Any],
    figures: Sequence[Mapping[str, Any]] = (),
    artifacts: Mapping[str, Any] = (),
    notes: Optional[str] = None,
    content_hashes: Optional[Mapping[str, Any]] = None,
    generated_at: Optional[str] = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at or utc_now_iso(),
        "run": dict(run),
        "metrics": coerce_json(metrics),
        "figures": [dict(f) for f in figures],
        "artifacts": coerce_json(artifacts),
    }
    if notes is not None:
        payload["notes"] = str(notes)
    if content_hashes is not None:
        payload["content_hashes"] = coerce_json(content_hashes)
    if extra:
        for k, v in extra.items():
            if k not in payload:
                payload[str(k)] = coerce_json(v)
    return validate_results_payload(payload)
