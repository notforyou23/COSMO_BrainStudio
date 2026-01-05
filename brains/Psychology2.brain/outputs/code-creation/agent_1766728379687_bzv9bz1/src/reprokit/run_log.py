"""Run logging utilities.

Provides structured run logs capturing timestamps, host/Python info, and installed
package versions. Logs are JSON or JSONL and are safe to append across runs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Union
import json
import os
import platform
import socket
import sys
import time
import traceback
from datetime import datetime, timezone
try:
    from importlib import metadata as _ilm
except Exception:  # pragma: no cover
    _ilm = None  # type: ignore
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_relpath(p: Path) -> str:
    try:
        return str(p.resolve())
    except Exception:
        return str(p)


def installed_packages() -> Dict[str, str]:
    """Return installed distributions as {name: version}, best-effort."""
    pkgs: Dict[str, str] = {}
    if _ilm is None:
        return pkgs
    try:
        for dist in _ilm.distributions():
            try:
                name = (dist.metadata.get("Name") or dist.name or "").strip()
                version = (dist.version or "").strip()
                if name:
                    pkgs[name] = version
            except Exception:
                continue
    except Exception:
        return {}
    return dict(sorted(pkgs.items(), key=lambda kv: kv[0].lower()))


def collect_run_metadata(extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Collect a structured metadata record suitable for logging."""
    meta: Dict[str, Any] = {
        "timestamp_utc": utc_now_iso(),
        "host": {
            "hostname": socket.gethostname(),
            "fqdn": socket.getfqdn(),
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_executable": sys.executable,
            "python_version": platform.python_version(),
        },
        "process": {
            "pid": os.getpid(),
            "cwd": os.getcwd(),
            "argv": list(sys.argv),
        },
        "packages": installed_packages(),
    }
    if extra:
        meta["extra"] = extra
    return meta


def write_run_log(
    log_path: Union[str, Path],
    record: Dict[str, Any],
    *,
    jsonl: bool = True,
    ensure_parent: bool = True,
) -> Path:
    """Write a log record to a path (JSONL append by default)."""
    p = Path(log_path)
    if ensure_parent:
        p.parent.mkdir(parents=True, exist_ok=True)
    if jsonl:
        line = json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n"
        with p.open("a", encoding="utf-8") as f:
            f.write(line)
    else:
        with p.open("w", encoding="utf-8") as f:
            json.dump(record, f, sort_keys=True, ensure_ascii=False, indent=2)
            f.write("\n")
    return p
@dataclass
class RunLogger:
    """Context manager to log start/end, duration, and exceptions."""

    log_path: Union[str, Path]
    run_name: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None
    jsonl: bool = True

    def __post_init__(self) -> None:
        self._t0: Optional[float] = None
        self._start_record: Optional[Dict[str, Any]] = None

    def start(self) -> Dict[str, Any]:
        self._t0 = time.time()
        rec = collect_run_metadata(extra=self.extra)
        rec["event"] = "run_start"
        if self.run_name:
            rec["run_name"] = self.run_name
        rec["log_path"] = _safe_relpath(Path(self.log_path))
        write_run_log(self.log_path, rec, jsonl=self.jsonl)
        self._start_record = rec
        return rec

    def end(self, status: str = "ok", error: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        t1 = time.time()
        rec: Dict[str, Any] = {
            "timestamp_utc": utc_now_iso(),
            "event": "run_end",
            "status": status,
            "duration_seconds": (t1 - (self._t0 or t1)),
        }
        if self.run_name:
            rec["run_name"] = self.run_name
        if error is not None:
            rec["error"] = error
        write_run_log(self.log_path, rec, jsonl=self.jsonl)
        return rec

    def __enter__(self) -> "RunLogger":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc is None:
            self.end(status="ok")
            return False
        err = {
            "type": getattr(exc_type, "__name__", str(exc_type)),
            "message": str(exc),
            "traceback": "".join(traceback.format_exception(exc_type, exc, tb)),
        }
        self.end(status="error", error=err)
        return False
def log_run(
    log_path: Union[str, Path],
    *,
    run_name: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
    jsonl: bool = True,
) -> RunLogger:
    """Convenience factory for RunLogger."""
    return RunLogger(log_path=log_path, run_name=run_name, extra=extra, jsonl=jsonl)


__all__ = [
    "RunLogger",
    "collect_run_metadata",
    "installed_packages",
    "log_run",
    "utc_now_iso",
    "write_run_log",
]
