from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional
import contextlib
import datetime as _dt
import hashlib
import json
import os
import platform
import socket
import subprocess
import sys
import tempfile
import time
def ensure_dir(path: Path) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def stable_json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path = Path(path)
    ensure_dir(path.parent)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.remove(tmp)


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    atomic_write_bytes(path, text.encode(encoding))


def write_json(path: Path, obj: Any) -> None:
    atomic_write_text(path, stable_json_dumps(obj) + "\n")


def _hash_obj(obj: Any) -> str:
    s = stable_json_dumps(obj)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]


def deterministic_output_dir(build_root: Path, config: Optional[Dict[str, Any]] = None, name: str = "run") -> Path:
    build_root = ensure_dir(Path(build_root))
    suffix = _hash_obj(config) if config is not None else "default"
    out = build_root / f"{name}_{suffix}"
    return ensure_dir(out)
def _git_info(cwd: Optional[Path] = None) -> Dict[str, Any]:
    cwd = Path(cwd) if cwd else Path.cwd()
    def run(args):
        return subprocess.check_output(args, cwd=str(cwd), stderr=subprocess.DEVNULL).decode("utf-8", "ignore").strip()
    info: Dict[str, Any] = {}
    try:
        info["commit"] = run(["git", "rev-parse", "HEAD"])
        info["branch"] = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        info["is_dirty"] = bool(run(["git", "status", "--porcelain"]))
    except Exception:
        return {}
    return info


def collect_env() -> Dict[str, Any]:
    return {
        "timestamp_utc": _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "python": sys.version.replace("\n", " "),
        "executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "hostname": socket.gethostname(),
        "cwd": str(Path.cwd()),
        "pid": os.getpid(),
        "git": _git_info(),
    }
@dataclass
class RunLogger:
    out_dir: Path
    params: Dict[str, Any] = field(default_factory=dict)
    run_name: str = "run"
    start_time: float = field(default_factory=time.time)
    _events_path: Path = field(init=False)

    def __post_init__(self) -> None:
        self.out_dir = ensure_dir(Path(self.out_dir))
        self._events_path = self.out_dir / "run_log.jsonl"
        meta = {
            "run_name": self.run_name,
            "params": self.params,
            "env": collect_env(),
        }
        write_json(self.out_dir / "run_meta.json", meta)
        self.event("start", {"meta_path": str(self.out_dir / "run_meta.json")})

    def event(self, name: str, data: Optional[Dict[str, Any]] = None, level: str = "INFO") -> None:
        rec = {
            "ts_utc": _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "level": level,
            "event": name,
            "data": data or {},
        }
        line = json.dumps(rec, ensure_ascii=False, sort_keys=True)
        ensure_dir(self._events_path.parent)
        with open(self._events_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def finalize(self, status: str = "ok", outputs: Optional[Dict[str, Any]] = None) -> Path:
        end = time.time()
        summary = {
            "run_name": self.run_name,
            "status": status,
            "duration_sec": round(end - self.start_time, 6),
            "params": self.params,
            "outputs": outputs or {},
            "env": collect_env(),
        }
        out_path = self.out_dir / "run_summary.json"
        write_json(out_path, summary)
        self.event("finalize", {"status": status, "summary_path": str(out_path)})
        return out_path
