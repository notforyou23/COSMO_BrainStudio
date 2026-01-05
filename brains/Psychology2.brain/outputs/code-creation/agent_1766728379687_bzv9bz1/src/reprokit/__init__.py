"""
reprokit: lightweight run logging utilities for reproducible outputs.

Public surface:
- write_run_log: write a structured JSON run log (timestamp, versions, git info).
- RunLogger: context manager that writes a run log on exit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
import json
import os
import platform
import subprocess
import sys

try:
    from importlib import metadata as importlib_metadata  # py>=3.8
except Exception:  # pragma: no cover
    import importlib_metadata  # type: ignore


__all__ = ["write_run_log", "RunLogger", "collect_env_info", "collect_package_versions"]
__version__ = "0.1.0"


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def collect_package_versions(packages: Sequence[str] | None = None) -> dict[str, str]:
    """
    Collect installed package versions.

    If packages is None, returns versions for a small, high-signal set of common
    scientific/runtime libraries when installed.
    """
    if packages is None:
        packages = ("reprokit", "pip", "setuptools", "wheel", "numpy", "pandas", "scipy", "matplotlib", "sklearn")
    versions: dict[str, str] = {}
    for name in packages:
        try:
            versions[name] = importlib_metadata.version(name)
        except Exception:
            continue
    return dict(sorted(versions.items()))


def _find_git_root(start: Path | None = None) -> Path | None:
    p = (start or Path.cwd()).resolve()
    for candidate in (p, *p.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _git_info(repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or _find_git_root()
    if root is None:
        return {"present": False}
    def _run(args: list[str]) -> str | None:
        try:
            out = subprocess.check_output(args, cwd=str(root), stderr=subprocess.DEVNULL, text=True).strip()
            return out or None
        except Exception:
            return None
    info = {
        "present": True,
        "root": str(root),
        "commit": _run(["git", "rev-parse", "HEAD"]),
        "branch": _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]),
        "dirty": None,
    }
    s = _run(["git", "status", "--porcelain"])
    if s is not None:
        info["dirty"] = (s != "")
    return info


def collect_env_info(
    packages: Sequence[str] | None = None,
    include_git: bool = True,
) -> dict[str, Any]:
    env = {
        "timestamp_utc": _now_utc_iso(),
        "python": {
            "version": sys.version.splitlines()[0],
            "executable": sys.executable,
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "process": {
            "pid": os.getpid(),
            "cwd": str(Path.cwd()),
            "argv": list(sys.argv),
        },
        "packages": collect_package_versions(packages),
    }
    if include_git:
        env["git"] = _git_info()
    return env


def write_run_log(
    output_dir: str | Path,
    run_name: str | None = None,
    extra: Mapping[str, Any] | None = None,
    packages: Sequence[str] | None = None,
    filename: str = "run_log.json",
    indent: int = 2,
) -> Path:
    """
    Write a JSON run log to output_dir/filename and return the written path.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    log: dict[str, Any] = collect_env_info(packages=packages, include_git=True)
    if run_name:
        log["run_name"] = run_name
    if extra:
        log["extra"] = dict(extra)
    path = out_dir / filename
    path.write_text(json.dumps(log, indent=indent, sort_keys=True) + "\n", encoding="utf-8")
    return path


@dataclass
class RunLogger:
    """
    Context manager for emitting a run log with start/end timestamps and duration.

    Example:
        with RunLogger("outputs", run_name="analysis") as rl:
            ...
            rl.extra["note"] = "added feature"
    """
    output_dir: str | Path
    run_name: str | None = None
    filename: str = "run_log.json"
    packages: Sequence[str] | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    _start: datetime | None = field(default=None, init=False, repr=False)
    _path: Path | None = field(default=None, init=False, repr=False)

    def __enter__(self) -> "RunLogger":
        self._start = datetime.now(timezone.utc)
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        end = datetime.now(timezone.utc)
        start = self._start or end
        duration_s = max(0.0, (end - start).total_seconds())
        self.extra.update(
            {
                "start_timestamp_utc": start.replace(microsecond=0).isoformat(),
                "end_timestamp_utc": end.replace(microsecond=0).isoformat(),
                "duration_seconds": duration_s,
                "exception": None if exc_type is None else {"type": getattr(exc_type, "__name__", str(exc_type)), "message": str(exc)},
            }
        )
        self._path = write_run_log(
            output_dir=self.output_dir,
            run_name=self.run_name,
            extra=self.extra,
            packages=self.packages,
            filename=self.filename,
        )
        return False

    @property
    def path(self) -> Path | None:
        return self._path
