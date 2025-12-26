from __future__ import annotations
from pathlib import Path
import dataclasses
import hashlib
import io
import json
import os
import tempfile
from typing import Any, Mapping, Optional, Union

Jsonable = Any


def _to_jsonable(obj: Any) -> Any:
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    if isinstance(obj, Path):
        return obj.as_posix()
    if isinstance(obj, (set, frozenset)):
        return sorted(_to_jsonable(x) for x in obj)
    if isinstance(obj, tuple):
        return [_to_jsonable(x) for x in obj]
    if isinstance(obj, (bytes, bytearray, memoryview)):
        return bytes(obj).hex()
    if isinstance(obj, Mapping):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_jsonable(x) for x in obj]
    return obj


def canonical_dumps(obj: Jsonable) -> str:
    canonical = _to_jsonable(obj)
    return json.dumps(
        canonical,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_dump_bytes(obj: Jsonable) -> bytes:
    return (canonical_dumps(obj) + "\n").encode("utf-8")


def stable_hash_bytes(data: Union[bytes, bytearray, memoryview], algo: str = "sha256") -> str:
    h = hashlib.new(algo)
    h.update(bytes(data))
    return h.hexdigest()


def stable_hash_text(text: str, algo: str = "sha256") -> str:
    return stable_hash_bytes(text.encode("utf-8"), algo=algo)


def stable_hash_file(path: Union[str, Path], algo: str = "sha256", chunk_size: int = 1024 * 1024) -> str:
    p = Path(path)
    h = hashlib.new(algo)
    with p.open("rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _atomic_write_bytes(path: Union[str, Path], data: bytes, mode: int = 0o644) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd = None
    tmp_path: Optional[Path] = None
    try:
        fd, tmp_name = tempfile.mkstemp(prefix=p.name + ".", suffix=".tmp", dir=str(p.parent))
        tmp_path = Path(tmp_name)
        with os.fdopen(fd, "wb") as f:
            fd = None
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp_path, mode)
        os.replace(str(tmp_path), str(p))
        tmp_path = None
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        if tmp_path is not None:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
    return p


def write_text_atomic(path: Union[str, Path], text: str, encoding: str = "utf-8", newline: bool = True) -> Path:
    if newline and not text.endswith("\n"):
        text += "\n"
    return _atomic_write_bytes(path, text.encode(encoding))


def write_json_atomic(path: Union[str, Path], obj: Jsonable) -> Path:
    return _atomic_write_bytes(path, canonical_dump_bytes(obj))


def read_json(path: Union[str, Path]) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def stable_hash_json_obj(obj: Jsonable, algo: str = "sha256") -> str:
    return stable_hash_bytes(canonical_dump_bytes(obj), algo=algo)
