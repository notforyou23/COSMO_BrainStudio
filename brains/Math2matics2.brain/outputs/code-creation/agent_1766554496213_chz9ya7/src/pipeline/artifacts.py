from __future__ import annotations

import io
import json
import os
import sys
import time
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union
PathLike = Union[str, Path]


def ensure_dir(path: PathLike) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
def _atomic_write(path: Path, data: bytes) -> None:
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
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass


def atomic_write_text(path: PathLike, text: str, encoding: str = "utf-8") -> None:
    _atomic_write(Path(path), text.encode(encoding))


def atomic_write_json(
    path: PathLike,
    obj: Any,
    *,
    indent: int = 2,
    sort_keys: bool = True,
    ensure_ascii: bool = False,
) -> None:
    data = json.dumps(obj, indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii) + "\n"
    atomic_write_text(path, data)
@dataclass(frozen=True)
class CanonicalArtifacts:
    outputs_dir: Path
    results_json: Path
    figure_png: Path
    run_stamp_json: Path
    run_log: Path


def canonical_artifacts(outputs_dir: PathLike = "outputs") -> CanonicalArtifacts:
    out = ensure_dir(outputs_dir)
    return CanonicalArtifacts(
        outputs_dir=out,
        results_json=out / "results.json",
        figure_png=out / "figure.png",
        run_stamp_json=out / "run_stamp.json",
        run_log=out / "run.log",
    )
def write_results(outputs_dir: PathLike, results: Dict[str, Any]) -> Path:
    arts = canonical_artifacts(outputs_dir)
    atomic_write_json(arts.results_json, results)
    return arts.results_json


def save_figure_path(outputs_dir: PathLike) -> Path:
    return canonical_artifacts(outputs_dir).figure_png
def _best_effort_git_info(cwd: Optional[Path] = None) -> Dict[str, Any]:
    import subprocess

    cwd = Path(cwd) if cwd is not None else None
    info: Dict[str, Any] = {}
    try:
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=cwd, stderr=subprocess.DEVNULL).decode().strip()
        info["git_sha"] = sha
        dirty = subprocess.call(["git", "diff", "--quiet"], cwd=cwd, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        info["git_dirty"] = bool(dirty)
    except Exception:
        pass
    return info


def write_run_stamp(
    outputs_dir: PathLike,
    *,
    seed: Optional[int] = None,
    extra: Optional[Dict[str, Any]] = None,
    include_git: bool = True,
) -> Path:
    arts = canonical_artifacts(outputs_dir)
    payload: Dict[str, Any] = {
        "created_utc": utc_now_iso(),
        "seed": seed,
        "pid": os.getpid(),
        "python": sys.version.split()[0],
        "argv": list(sys.argv),
        "cwd": str(Path.cwd()),
        "platform": sys.platform,
        "time_time": time.time(),
    }
    if include_git:
        payload.update(_best_effort_git_info(Path.cwd()))
    if extra:
        payload.update(extra)
    atomic_write_json(arts.run_stamp_json, payload)
    return arts.run_stamp_json
def append_run_log(outputs_dir: PathLike, line: str) -> Path:
    arts = canonical_artifacts(outputs_dir)
    ensure_dir(arts.outputs_dir)
    msg = line.rstrip("\n") + "\n"
    with open(arts.run_log, "a", encoding="utf-8") as f:
        f.write(msg)
    return arts.run_log


class RunLogger:
    def __init__(self, outputs_dir: PathLike):
        self._arts = canonical_artifacts(outputs_dir)

    @property
    def path(self) -> Path:
        return self._arts.run_log

    def write(self, line: str) -> None:
        append_run_log(self._arts.outputs_dir, line)

    def printf(self, fmt: str, *args: Any, **kwargs: Any) -> None:
        self.write(fmt.format(*args, **kwargs))


def open_run_logger(outputs_dir: PathLike) -> RunLogger:
    return RunLogger(outputs_dir)
