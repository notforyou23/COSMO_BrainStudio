from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import platform
import tempfile
from typing import Any, Mapping, Optional, TextIO


DEFAULT_LOG_DIR = Path("runtime") / "_build" / "logs"
LOG_BASENAME = "run.log"
ENV_BASENAME = "env.json"
CONFIG_BASENAME = "config.json"
SUMMARY_BASENAME = "run_summary.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_jsonable(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, Path):
        return str(obj)
    if is_dataclass(obj):
        return _to_jsonable(asdict(obj))
    if isinstance(obj, Mapping):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_to_jsonable(v) for v in obj]
    if hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
        return _to_jsonable(obj.model_dump())
    if hasattr(obj, "dict") and callable(getattr(obj, "dict")):
        return _to_jsonable(obj.dict())
    return str(obj)


def repo_root(start: Optional[Path] = None) -> Path:
    p = (start or Path.cwd()).resolve()
    for _ in range(10):
        if (p / "runtime").exists() or (p / "src").exists() or (p / "pyproject.toml").exists():
            return p
        if p.parent == p:
            break
        p = p.parent
    return (start or Path.cwd()).resolve()
def logs_dir(root: Optional[Path] = None) -> Path:
    return (root or repo_root()) / DEFAULT_LOG_DIR


def ensure_logs_dir(root: Optional[Path] = None) -> Path:
    d = logs_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    return d


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("wb", delete=False, dir=str(path.parent)) as f:
        tmp = Path(f.name)
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    atomic_write_bytes(path, text.encode(encoding))


def atomic_write_json(path: Path, obj: Any) -> None:
    payload = json.dumps(_to_jsonable(obj), indent=2, sort_keys=True, ensure_ascii=False) + "
"
    atomic_write_text(path, payload)


def open_run_log(root: Optional[Path] = None, mode: str = "a", encoding: str = "utf-8") -> tuple[Path, TextIO]:
    d = ensure_logs_dir(root)
    p = d / LOG_BASENAME
    fh = open(p, mode, encoding=encoding)
    return p, fh
def write_env_snapshot(root: Optional[Path] = None, extra: Optional[Mapping[str, Any]] = None) -> Path:
    d = ensure_logs_dir(root)
    p = d / ENV_BASENAME
    snap: dict[str, Any] = {
        "timestamp_utc": utc_now_iso(),
        "cwd": str(Path.cwd()),
        "python": {
            "executable": os.environ.get("PYTHON", "") or getattr(os, "executable", ""),
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
        },
        "env": dict(os.environ),
    }
    if extra:
        snap["extra"] = _to_jsonable(dict(extra))
    atomic_write_json(p, snap)
    return p


def write_config(root: Optional[Path] = None, config: Any = None) -> Path:
    d = ensure_logs_dir(root)
    p = d / CONFIG_BASENAME
    atomic_write_json(p, {} if config is None else config)
    return p
def default_run_summary() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "timestamp_utc": utc_now_iso(),
        "status": "unknown",
        "exit_code": None,
        "timing": {"started_utc": None, "ended_utc": None},
        "container": {
            "id": None,
            "image": None,
            "lost": False,
            "lost_detected_utc": None,
            "lost_reason": None,
        },
        "artifacts": {
            "log_path": str(DEFAULT_LOG_DIR / LOG_BASENAME),
            "env_path": str(DEFAULT_LOG_DIR / ENV_BASENAME),
            "config_path": str(DEFAULT_LOG_DIR / CONFIG_BASENAME),
            "summary_path": str(DEFAULT_LOG_DIR / SUMMARY_BASENAME),
        },
    }


def mark_container_lost(summary: Mapping[str, Any], reason: Optional[str] = None, when_utc: Optional[str] = None) -> dict[str, Any]:
    s = _to_jsonable(dict(summary))
    c = s.setdefault("container", {})
    c["lost"] = True
    c["lost_detected_utc"] = when_utc or utc_now_iso()
    if reason is not None:
        c["lost_reason"] = str(reason)
    return s


def write_run_summary(root: Optional[Path] = None, summary: Any = None) -> Path:
    d = ensure_logs_dir(root)
    p = d / SUMMARY_BASENAME
    atomic_write_json(p, default_run_summary() if summary is None else summary)
    return p
