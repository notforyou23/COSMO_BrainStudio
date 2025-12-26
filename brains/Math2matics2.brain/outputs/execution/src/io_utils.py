from __future__ import annotations

import io
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping, Optional, Union

PathLike = Union[str, os.PathLike, Path]


def ensure_dir(path: PathLike) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def ensure_outputs_dir(root: Optional[PathLike] = None) -> Path:
    base = Path(root) if root is not None else Path.cwd()
    return ensure_dir(base / "outputs")


def _fsync_file(f) -> None:
    try:
        f.flush()
        os.fsync(f.fileno())
    except Exception:
        pass


def atomic_write_bytes(path: PathLike, data: bytes) -> Path:
    path = Path(path)
    ensure_dir(path.parent)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            _fsync_file(f)
        os.replace(tmp_name, path)
    finally:
        try:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
        except Exception:
            pass
    try:
        dfd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    except Exception:
        pass
    return path


def atomic_write_text(path: PathLike, text: str, encoding: str = "utf-8") -> Path:
    return atomic_write_bytes(path, text.encode(encoding))


def _json_default(obj: Any) -> Any:
    if isinstance(obj, Path):
        return str(obj)
    item = getattr(obj, "item", None)
    if callable(item):
        try:
            return item()
        except Exception:
            pass
    tolist = getattr(obj, "tolist", None)
    if callable(tolist):
        try:
            return tolist()
        except Exception:
            pass
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def stable_json_dumps(obj: Any) -> str:
    return json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
        default=_json_default,
    )


def write_json_atomic(path: PathLike, obj: Any) -> Path:
    text = stable_json_dumps(obj) + "\n"
    return atomic_write_text(path, text)


def read_json(path: PathLike) -> Any:
    with open(Path(path), "r", encoding="utf-8") as f:
        return json.load(f)


def write_bytes_if_changed(path: PathLike, data: bytes) -> Path:
    path = Path(path)
    try:
        existing = path.read_bytes()
        if existing == data:
            return path
    except Exception:
        pass
    return atomic_write_bytes(path, data)
