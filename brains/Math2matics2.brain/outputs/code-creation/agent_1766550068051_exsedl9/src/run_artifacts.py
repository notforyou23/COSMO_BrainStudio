from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
from typing import Any, Dict, Tuple

SCHEMA_VERSION = 1
DETERMINISTIC_RUN_ID = "deterministic-run"
DETERMINISTIC_CREATED_UTC = "1970-01-01T00:00:00Z"

RUN_STAMP_SCHEMA_KEYS = (
    "schema_version",
    "run_id",
    "created_utc",
    "artifacts",
    "content_hash",
)

ARTIFACTS_KEYS = ("run_stamp", "run_log")
def _stable_json_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def _atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding=encoding, newline="\n")
    os.replace(tmp, path)


def _fnv1a_32(data: bytes) -> str:
    h = 2166136261
    for b in data:
        h ^= b
        h = (h * 16777619) & 0xFFFFFFFF
    return f"{h:08x}
def build_run_log_text() -> str:
    lines = [
        "run_id=deterministic-run",
        "created_utc=1970-01-01T00:00:00Z",
        "status=ok",
        "message=deterministic artifacts generated",
    ]
    return "\n".join(lines) + "\n"


def build_run_stamp_dict(outputs_dir: Path) -> Dict[str, Any]:
    outputs_dir = Path(outputs_dir)
    stamp_rel = "outputs/run_stamp.json"
    log_rel = "outputs/run.log"
    artifacts = {"run_stamp": stamp_rel, "run_log": log_rel}
    seed = {
        "schema_version": SCHEMA_VERSION,
        "run_id": DETERMINISTIC_RUN_ID,
        "created_utc": DETERMINISTIC_CREATED_UTC,
        "artifacts": artifacts,
    }
    content_hash = _fnv1a_32(_stable_json_dumps(seed).encode("utf-8"))
    seed["content_hash"] = content_hash
    return seed
def validate_run_stamp(obj: Any) -> Tuple[bool, str]:
    if not isinstance(obj, dict):
        return False, "run_stamp must be a JSON object"
    extra = set(obj.keys()) - set(RUN_STAMP_SCHEMA_KEYS)
    missing = set(RUN_STAMP_SCHEMA_KEYS) - set(obj.keys())
    if missing:
        return False, f"missing keys: {sorted(missing)}"
    if extra:
        return False, f"unexpected keys: {sorted(extra)}"
    if obj["schema_version"] != SCHEMA_VERSION:
        return False, "schema_version mismatch"
    if obj["run_id"] != DETERMINISTIC_RUN_ID:
        return False, "run_id mismatch"
    if obj["created_utc"] != DETERMINISTIC_CREATED_UTC:
        return False, "created_utc mismatch"
    artifacts = obj["artifacts"]
    if not isinstance(artifacts, dict):
        return False, "artifacts must be an object"
    if set(artifacts.keys()) != set(ARTIFACTS_KEYS):
        return False, "artifacts keys mismatch"
    if artifacts["run_stamp"] != "outputs/run_stamp.json":
        return False, "artifacts.run_stamp mismatch"
    if artifacts["run_log"] != "outputs/run.log":
        return False, "artifacts.run_log mismatch"
    expected = build_run_stamp_dict(Path("."))
    if obj["content_hash"] != expected["content_hash"]:
        return False, "content_hash mismatch"
    if not isinstance(obj["content_hash"], str) or len(obj["content_hash"]) != 8:
        return False, "content_hash format invalid"
    return True, "ok"


def assert_valid_run_stamp(obj: Any) -> None:
    ok, msg = validate_run_stamp(obj)
    if not ok:
        raise ValueError(msg)
@dataclass(frozen=True)
class RunArtifacts:
    outputs_dir: Path

    @property
    def run_stamp_path(self) -> Path:
        return self.outputs_dir / "run_stamp.json"

    @property
    def run_log_path(self) -> Path:
        return self.outputs_dir / "run.log"


def write_run_artifacts(outputs_dir: Path) -> RunArtifacts:
    outputs_dir = Path(outputs_dir)
    artifacts = RunArtifacts(outputs_dir=outputs_dir)
    log_text = build_run_log_text()
    stamp = build_run_stamp_dict(outputs_dir)
    _atomic_write_text(artifacts.run_log_path, log_text)
    _atomic_write_text(artifacts.run_stamp_path, _stable_json_dumps(stamp))
    return artifacts
