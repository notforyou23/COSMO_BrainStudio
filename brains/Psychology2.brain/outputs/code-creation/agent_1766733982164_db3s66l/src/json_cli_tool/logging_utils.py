from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Union


JsonObj = Union[Dict[str, Any], list, str, int, float, bool, None]


def utc_timestamp_for_dir(dt: Optional[datetime] = None) -> str:
    """Return UTC timestamp formatted as YYYYMMDD_HHMMSS for run dir names."""
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.strftime("%Y%m%d_%H%M%S")


def create_run_dir(outputs_dir: Union[str, Path], prefix: str = "run_") -> Path:
    """Create outputs/logs/run_YYYYMMDD_HHMMSS (UTC); disambiguate with _N if needed."""
    outputs_dir = Path(outputs_dir)
    logs_dir = outputs_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    base_name = f"{prefix}{utc_timestamp_for_dir()}"
    run_dir = logs_dir / base_name
    if not run_dir.exists():
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir

    i = 2
    while True:
        candidate = logs_dir / f"{base_name}_{i}"
        try:
            candidate.mkdir(parents=True, exist_ok=False)
            return candidate
        except FileExistsError:
            i += 1


def _atomic_replace(tmp_path: Path, final_path: Path) -> None:
    final_path.parent.mkdir(parents=True, exist_ok=True)
    os.replace(str(tmp_path), str(final_path))


def atomic_write_text(path: Union[str, Path], text: str, encoding: str = "utf-8") -> Path:
    """Atomically write text to path by writing to a temp file in the same directory."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fd = None
    tmp_path: Optional[Path] = None
    try:
        fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
        tmp_path = Path(tmp_name)
        with os.fdopen(fd, "w", encoding=encoding, newline="") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        fd = None
        _atomic_replace(tmp_path, path)
        return path
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def atomic_write_json(
    path: Union[str, Path],
    obj: JsonObj,
    encoding: str = "utf-8",
    indent: int = 2,
    sort_keys: bool = True,
) -> Path:
    """Atomically write JSON with stable formatting."""
    text = json.dumps(obj, ensure_ascii=False, indent=indent, sort_keys=sort_keys) + "\n"
    return atomic_write_text(path, text, encoding=encoding)


@dataclass(frozen=True)
class RunLogPaths:
    run_dir: Path
    console_log: Path
    structured_log: Path


def write_console_log(run_dir: Union[str, Path], console_text: str, filename: str = "console.log") -> Path:
    """Write console output to run_dir/filename atomically."""
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    return atomic_write_text(run_dir / filename, console_text)


def write_structured_log(
    run_dir: Union[str, Path],
    log_obj: Dict[str, Any],
    filename: str = "structured_log.json",
) -> Path:
    """Write a structured JSON log to run_dir/filename atomically."""
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    return atomic_write_json(run_dir / filename, log_obj)


def init_run_logs(outputs_dir: Union[str, Path]) -> RunLogPaths:
    """Create a run directory and return conventional log file paths."""
    outputs_dir = Path(outputs_dir)
    run_dir = create_run_dir(outputs_dir)
    return RunLogPaths(
        run_dir=run_dir,
        console_log=run_dir / "console.log",
        structured_log=run_dir / "structured_log.json",
    )
