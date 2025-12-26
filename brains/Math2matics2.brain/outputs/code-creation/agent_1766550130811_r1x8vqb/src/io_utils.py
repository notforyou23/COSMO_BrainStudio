from __future__ import annotations

from pathlib import Path
import json
import os
import tempfile
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Union


PathLike = Union[str, os.PathLike]


def ensure_outputs_dir(base_dir: Optional[PathLike] = None) -> Path:
    """
    Ensure an ./outputs directory exists.
    If base_dir is None, uses the current working directory.
    """
    root = Path(base_dir) if base_dir is not None else Path.cwd()
    out = root / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _now_iso_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def atomic_write_json(path: PathLike, obj: Any, *, indent: int = 2, sort_keys: bool = True) -> Path:
    """
    Atomically write JSON by writing to a temp file in the same directory then replacing.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    fd = None
    tmp_path = None
    try:
        fd, tmp_path_str = tempfile.mkstemp(prefix=p.name + ".", suffix=".tmp", dir=str(p.parent))
        tmp_path = Path(tmp_path_str)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            fd = None
            json.dump(obj, f, indent=indent, sort_keys=sort_keys)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(str(tmp_path), str(p))
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
    return p


def save_results_json(outputs_dir: PathLike, results: Any, *, filename: str = "results.json") -> Path:
    """
    Save results to outputs/results.json (or custom filename) using atomic write.
    """
    out = ensure_outputs_dir(outputs_dir)
    return atomic_write_json(out / filename, results)


def append_run_log(
    outputs_dir: PathLike,
    record: Union[str, Mapping[str, Any]],
    *,
    log_name: str = "run.log",
) -> Path:
    """
    Append a single line to an append-only run log in outputs/.
    If record is a dict-like mapping, it is written as a JSON line with a timestamp.
    If record is a string, it is written verbatim (with a timestamp prefix).
    """
    out = ensure_outputs_dir(outputs_dir)
    log_path = out / log_name

    if isinstance(record, str):
        line = f"{_now_iso_utc()}\t{record}".rstrip("\n") + "\n"
    else:
        payload = dict(record)
        payload.setdefault("ts_utc", _now_iso_utc())
        line = json.dumps(payload, sort_keys=True) + "\n"

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
        os.fsync(f.fileno())
    return log_path
