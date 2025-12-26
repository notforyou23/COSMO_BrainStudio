from __future__ import annotations

from pathlib import Path
import os
import re
import json
import tempfile
import hashlib
from datetime import datetime, timezone
from typing import Any, Optional, Union


PathLike = Union[str, os.PathLike, Path]
def ensure_dir(path: PathLike) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def utc_timestamp(compact: bool = True) -> str:
    dt = now_utc()
    if compact:
        return dt.strftime("%Y%m%dT%H%M%SZ")
    return dt.isoformat().replace("+00:00", "Z")
_SLUG_RE = re.compile(r"[^a-z0-9]+", re.IGNORECASE)


def slugify(text: str, max_len: int = 80) -> str:
    s = (text or "").strip().lower()
    s = _SLUG_RE.sub("-", s).strip("-")
    if not s:
        s = "item"
    return s[:max_len].strip("-")
def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fsync_dir(path: Path) -> None:
    dpath = path if path.is_dir() else path.parent
    try:
        fd = os.open(str(dpath), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
def atomic_write_bytes(path: PathLike, data: bytes, mode: int = 0o644) -> Path:
    dst = Path(path)
    ensure_dir(dst.parent)
    tmp_fd: Optional[int] = None
    tmp_path: Optional[Path] = None
    try:
        tmp_fd, tmp_name = tempfile.mkstemp(prefix=dst.name + ".", suffix=".tmp", dir=str(dst.parent))
        tmp_path = Path(tmp_name)
        with os.fdopen(tmp_fd, "wb", closefd=False) as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp_path, mode)
        os.replace(str(tmp_path), str(dst))
        _fsync_dir(dst)
    finally:
        if tmp_fd is not None:
            try:
                os.close(tmp_fd)
            except OSError:
                pass
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
    return dst


def atomic_write_text(
    path: PathLike,
    text: str,
    encoding: str = "utf-8",
    newline: str = "\n",
    mode: int = 0o644,
) -> Path:
    if newline != "\n":
        text = text.replace("\n", newline)
    data = text.encode(encoding)
    return atomic_write_bytes(path, data, mode=mode)
def read_text(path: PathLike, encoding: str = "utf-8") -> str:
    return Path(path).read_text(encoding=encoding)


def read_json(path: PathLike, default: Any = None) -> Any:
    p = Path(path)
    if not p.exists():
        return default
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json_atomic(
    path: PathLike,
    obj: Any,
    indent: int = 2,
    sort_keys: bool = True,
) -> Path:
    text = json.dumps(obj, ensure_ascii=False, indent=indent, sort_keys=sort_keys) + "\n"
    return atomic_write_text(path, text)
def stable_run_dir(base_dir: PathLike, name: str, timestamp: Optional[str] = None) -> Path:
    base = ensure_dir(base_dir)
    ts = timestamp or utc_timestamp(compact=True)
    d = base / f"{ts}-{slugify(name, max_len=40)}"
    ensure_dir(d)
    return d
