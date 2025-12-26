"""Schema contract for outputs/run_stamp.json.

This module is shared by the entrypoint script and pytest to keep the
run-stamp schema/version contract consistent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

RUN_STAMP_SCHEMA_NAME = "pipeline.run_stamp"
RUN_STAMP_SCHEMA_VERSION = "1.0"

REQUIRED_TOP_LEVEL_FIELDS = (
    "schema_name",
    "schema_version",
    "pipeline_version",
    "run_id",
    "seed",
    "created_at",
    "outputs",
)

REQUIRED_OUTPUT_FIELDS = (
    "run_stamp_path",
    "run_log_path",
)

_ALLOWED_TOP_LEVEL = set(REQUIRED_TOP_LEVEL_FIELDS) | {"meta"}
_ALLOWED_OUTPUT_LEVEL = set(REQUIRED_OUTPUT_FIELDS)


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    errors: Tuple[str, ...] = ()


def _is_str(x: Any) -> bool:
    return isinstance(x, str) and len(x) > 0


def _is_int(x: Any) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _err(errors: List[str], msg: str) -> None:
    errors.append(msg)


def validate_run_stamp(stamp: Mapping[str, Any]) -> ValidationResult:
    """Validate a run-stamp mapping against the schema contract."""
    errors: List[str] = []
    if not isinstance(stamp, Mapping):
        return ValidationResult(False, ("stamp must be a mapping/dict",))

    for k in REQUIRED_TOP_LEVEL_FIELDS:
        if k not in stamp:
            _err(errors, f"missing required field: {k}")

    extra_top = set(stamp.keys()) - _ALLOWED_TOP_LEVEL
    if extra_top:
        _err(errors, f"unexpected top-level fields: {sorted(extra_top)!r}")

    if "schema_name" in stamp and stamp.get("schema_name") != RUN_STAMP_SCHEMA_NAME:
        _err(
            errors,
            f"schema_name must be {RUN_STAMP_SCHEMA_NAME!r}, got {stamp.get('schema_name')!r}",
        )

    if "schema_version" in stamp and stamp.get("schema_version") != RUN_STAMP_SCHEMA_VERSION:
        _err(
            errors,
            f"schema_version must be {RUN_STAMP_SCHEMA_VERSION!r}, got {stamp.get('schema_version')!r}",
        )

    if "pipeline_version" in stamp and not _is_str(stamp.get("pipeline_version")):
        _err(errors, "pipeline_version must be a non-empty string")

    if "run_id" in stamp and not _is_str(stamp.get("run_id")):
        _err(errors, "run_id must be a non-empty string")

    if "seed" in stamp and not _is_int(stamp.get("seed")):
        _err(errors, "seed must be an int")

    if "created_at" in stamp and not _is_str(stamp.get("created_at")):
        _err(errors, "created_at must be a non-empty string (ISO-8601 recommended)")

    outputs = stamp.get("outputs")
    if "outputs" in stamp and not isinstance(outputs, Mapping):
        _err(errors, "outputs must be an object/dict")
    elif isinstance(outputs, Mapping):
        for k in REQUIRED_OUTPUT_FIELDS:
            if k not in outputs:
                _err(errors, f"missing required outputs field: outputs.{k}")
        extra_out = set(outputs.keys()) - _ALLOWED_OUTPUT_LEVEL
        if extra_out:
            _err(errors, f"unexpected outputs fields: {sorted(extra_out)!r}")
        if "run_stamp_path" in outputs and not _is_str(outputs.get("run_stamp_path")):
            _err(errors, "outputs.run_stamp_path must be a non-empty string")
        if "run_log_path" in outputs and not _is_str(outputs.get("run_log_path")):
            _err(errors, "outputs.run_log_path must be a non-empty string")

    meta = stamp.get("meta")
    if "meta" in stamp and meta is not None and not isinstance(meta, Mapping):
        _err(errors, "meta must be an object/dict when present")

    return ValidationResult(ok=(len(errors) == 0), errors=tuple(errors))


def assert_valid_run_stamp(stamp: Mapping[str, Any]) -> None:
    """Raise ValueError with details if stamp is invalid."""
    res = validate_run_stamp(stamp)
    if not res.ok:
        raise ValueError("Invalid run_stamp.json: " + "; ".join(res.errors))


def make_run_stamp(
    *,
    pipeline_version: str,
    run_id: str,
    seed: int,
    created_at: str,
    run_stamp_path: str,
    run_log_path: str,
    meta: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a run-stamp dict conforming to this schema."""
    stamp: Dict[str, Any] = {
        "schema_name": RUN_STAMP_SCHEMA_NAME,
        "schema_version": RUN_STAMP_SCHEMA_VERSION,
        "pipeline_version": pipeline_version,
        "run_id": run_id,
        "seed": int(seed),
        "created_at": created_at,
        "outputs": {
            "run_stamp_path": run_stamp_path,
            "run_log_path": run_log_path,
        },
    }
    if meta is not None:
        stamp["meta"] = dict(meta)
    assert_valid_run_stamp(stamp)
    return stamp
