from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple, Union
import json
import os
import platform
import sys

ARTIFACT_VERSION = 1

RUN_STAMP_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["artifact_version", "run_id", "created_utc", "seed", "command", "python", "platform"],
    "properties": {
        "artifact_version": {"type": "integer"},
        "run_id": {"type": "string"},
        "created_utc": {"type": "string"},
        "seed": {"type": "integer"},
        "command": {"type": "array", "items": {"type": "string"}},
        "python": {"type": "string"},
        "platform": {"type": "string"},
    },
}

RESULTS_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["artifact_version", "run_id", "metrics", "params"],
    "properties": {
        "artifact_version": {"type": "integer"},
        "run_id": {"type": "string"},
        "metrics": {"type": "object"},
        "params": {"type": "object"},
    },
}

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def stable_json_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n"

def _atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding=encoding)
    os.replace(tmp, path)

def _is_iso_z(s: str) -> bool:
    if not isinstance(s, str) or not s.endswith("Z"):
        return False
    try:
        datetime.fromisoformat(s[:-1] + "+00:00")
        return True
    except Exception:
        return False

def _require_keys(d: Mapping[str, Any], keys: Sequence[str], where: str) -> None:
    missing = [k for k in keys if k not in d]
    if missing:
        raise ValueError(f"{where}: missing required keys: {missing}")

def validate_run_stamp(stamp: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(stamp, Mapping):
        raise TypeError("run_stamp must be a mapping")
    _require_keys(stamp, RUN_STAMP_SCHEMA["required"], "run_stamp")
    out = dict(stamp)
    if out["artifact_version"] != ARTIFACT_VERSION:
        raise ValueError("run_stamp.artifact_version mismatch")
    if not isinstance(out["run_id"], str) or not out["run_id"]:
        raise TypeError("run_stamp.run_id must be non-empty string")
    if not _is_iso_z(out["created_utc"]):
        raise ValueError("run_stamp.created_utc must be ISO-8601 UTC ending with 'Z'")
    if not isinstance(out["seed"], int):
        raise TypeError("run_stamp.seed must be int")
    cmd = out["command"]
    if not isinstance(cmd, list) or any(not isinstance(x, str) for x in cmd):
        raise TypeError("run_stamp.command must be list[str]")
    if not isinstance(out["python"], str) or not out["python"]:
        raise TypeError("run_stamp.python must be string")
    if not isinstance(out["platform"], str) or not out["platform"]:
        raise TypeError("run_stamp.platform must be string")
    return out

def validate_results(results: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(results, Mapping):
        raise TypeError("results must be a mapping")
    _require_keys(results, RESULTS_SCHEMA["required"], "results")
    out = dict(results)
    if out["artifact_version"] != ARTIFACT_VERSION:
        raise ValueError("results.artifact_version mismatch")
    if not isinstance(out["run_id"], str) or not out["run_id"]:
        raise TypeError("results.run_id must be non-empty string")
    if not isinstance(out["metrics"], Mapping):
        raise TypeError("results.metrics must be object")
    if not isinstance(out["params"], Mapping):
        raise TypeError("results.params must be object")
    return out

def write_json(path: Union[str, Path], obj: Any) -> None:
    p = Path(path)
    _atomic_write_text(p, stable_json_dumps(obj))

def write_run_stamp(path: Union[str, Path], *, run_id: str, seed: int, command: Sequence[str]) -> Dict[str, Any]:
    stamp = {
        "artifact_version": ARTIFACT_VERSION,
        "run_id": str(run_id),
        "created_utc": utc_now_iso(),
        "seed": int(seed),
        "command": list(command),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
    }
    stamp = validate_run_stamp(stamp)
    write_json(path, stamp)
    return stamp

def write_results(path: Union[str, Path], results: Mapping[str, Any]) -> Dict[str, Any]:
    out = validate_results(results)
    write_json(path, out)
    return out

def write_run_log(path: Union[str, Path], lines: Iterable[str]) -> None:
    p = Path(path)
    text = "".join((ln if ln.endswith("\n") else ln + "\n") for ln in lines)
    _atomic_write_text(p, text)

def make_log_lines(*, run_stamp: Mapping[str, Any], extra: Optional[Mapping[str, Any]] = None) -> List[str]:
    rs = validate_run_stamp(run_stamp)
    base = [
        f"artifact_version={rs['artifact_version']}",
        f"run_id={rs['run_id']}",
        f"created_utc={rs['created_utc']}",
        f"seed={rs['seed']}",
        f"command={json.dumps(rs['command'], ensure_ascii=False)}",
        f"python={rs['python']}",
        f"platform={rs['platform']}",
    ]
    if extra:
        for k in sorted(extra.keys()):
            base.append(f"{k}={extra[k]}")
    return base
