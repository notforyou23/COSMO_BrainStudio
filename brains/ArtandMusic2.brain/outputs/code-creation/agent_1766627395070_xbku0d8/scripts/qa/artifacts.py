from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
import datetime as _dt
import json
import os
import socket
import traceback
import uuid
def _utcnow() -> _dt.datetime:
    return _dt.datetime.now(tz=_dt.timezone.utc)

def utc_iso() -> str:
    return _utcnow().isoformat(timespec="seconds").replace("+00:00", "Z")

def _safe_mkdir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def _atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    _safe_mkdir(path.parent)
    tmp = path.with_suffix(path.suffix + f".tmp-{uuid.uuid4().hex}")
    tmp.write_text(text, encoding=encoding)
    tmp.replace(path)

def write_json(path: Path, obj: Any) -> None:
    _atomic_write_text(path, json.dumps(obj, indent=2, sort_keys=True) + "\n")

def write_text(path: Path, text: str) -> None:
    _atomic_write_text(path, text if text.endswith("\n") else text + "\n")

def append_text(path: Path, text: str) -> None:
    _safe_mkdir(path.parent)
    with path.open("a", encoding="utf-8") as f:
        f.write(text if text.endswith("\n") else text + "\n")

def _exc_to_dict(exc: BaseException) -> Dict[str, Any]:
    return {
        "type": type(exc).__name__,
        "message": str(exc),
        "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
    }
def default_outputs_root(cwd: Optional[Path] = None) -> Path:
    base = Path(os.environ.get("QA_OUTPUT_DIR", "")).expanduser()
    if str(base):
        return base
    cwd = cwd or Path.cwd()
    return cwd / "outputs" / "qa"

def new_run_id(prefix: str = "qa") -> str:
    ts = _utcnow().strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{ts}-{uuid.uuid4().hex[:8]}"

def ensure_run_dirs(run_dir: Path) -> Dict[str, Path]:
    run_dir = _safe_mkdir(run_dir)
    paths = {
        "run": run_dir,
        "logs": _safe_mkdir(run_dir / "logs"),
        "errors": _safe_mkdir(run_dir / "errors"),
        "partial": _safe_mkdir(run_dir / "partial"),
        "meta": _safe_mkdir(run_dir / "meta"),
    }
    return paths
@dataclass(frozen=True)
class Artifacts:
    root: Path
    run_id: str
    run_dir: Path

    @classmethod
    def create(cls, root: Optional[Path] = None, run_id: Optional[str] = None, prefix: str = "qa") -> "Artifacts":
        root = (root or default_outputs_root()).expanduser()
        run_id = run_id or new_run_id(prefix=prefix)
        run_dir = root / run_id
        ensure_run_dirs(run_dir)
        return cls(root=root, run_id=run_id, run_dir=run_dir)

    @property
    def paths(self) -> Dict[str, Path]:
        return ensure_run_dirs(self.run_dir)

    def write_run_metadata(self, **meta: Any) -> Path:
        data = {
            "run_id": self.run_id,
            "created_at": utc_iso(),
            "hostname": socket.gethostname(),
            "pid": os.getpid(),
            "cwd": str(Path.cwd()),
            **meta,
        }
        p = self.run_dir / "run.json"
        write_json(p, data)
        return p

    def write_summary(self, status: str, exit_code: Optional[int] = None, **extra: Any) -> Path:
        data = {"run_id": self.run_id, "status": status, "exit_code": exit_code, "ended_at": utc_iso(), **extra}
        p = self.run_dir / "summary.json"
        write_json(p, data)
        return p

    def write_log(self, name: str, text: str, append: bool = True) -> Path:
        p = self.run_dir / "logs" / f"{name}.log"
        (append_text if append else write_text)(p, text)
        return p

    def write_partial_results(self, name: str, obj: Any) -> Path:
        p = self.run_dir / "partial" / f"{name}.json"
        write_json(p, obj)
        return p

    def write_error(self, name: str, exc: Optional[BaseException] = None, *, message: Optional[str] = None,
                    exit_code: Optional[int] = None, where: Optional[str] = None, extra: Optional[Dict[str, Any]] = None) -> Path:
        data: Dict[str, Any] = {
            "run_id": self.run_id,
            "created_at": utc_iso(),
            "name": name,
            "where": where,
            "exit_code": exit_code,
            "message": message,
        }
        if exc is not None:
            data["exception"] = _exc_to_dict(exc)
        if extra:
            data["extra"] = extra
        p = self.run_dir / "errors" / f"{name}.json"
        write_json(p, data)
        return p
def write_index(root: Path, run_id: str, status: str, mode: Optional[str] = None) -> Path:
    root = root.expanduser()
    _safe_mkdir(root)
    p = root / "index.json"
    entry = {"run_id": run_id, "status": status, "mode": mode, "updated_at": utc_iso()}
    try:
        if p.exists():
            obj = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(obj, dict):
                obj = {}
        else:
            obj = {}
    except Exception:
        obj = {}
    obj["latest"] = entry
    write_json(p, obj)
    return p
