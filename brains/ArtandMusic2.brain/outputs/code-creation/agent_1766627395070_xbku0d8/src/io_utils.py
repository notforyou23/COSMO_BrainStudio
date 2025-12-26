from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os
import tempfile
from typing import Any, Dict, Optional, Union

PathLike = Union[str, os.PathLike, Path]
def ensure_dir(path: PathLike) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
def normalize_newlines(text: str) -> str:
    # Normalize CRLF/CR to LF deterministically
    return text.replace("\r\n", "\n").replace("\r", "\n")
def stable_json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
def content_hash(text: str, *, normalize: bool = True, encoding: str = "utf-8") -> str:
    if normalize:
        text = normalize_newlines(text)
    return sha256_bytes(text.encode(encoding))
def file_hash(path: PathLike, *, normalize: bool = False, encoding: str = "utf-8") -> str:
    p = Path(path)
    data: bytes
    if normalize:
        text = p.read_text(encoding=encoding)
        text = normalize_newlines(text)
        data = text.encode(encoding)
    else:
        data = p.read_bytes()
    return sha256_bytes(data)
def atomic_write_text(
    path: PathLike,
    text: str,
    *,
    encoding: str = "utf-8",
    normalize: bool = True,
    fsync: bool = True,
) -> None:
    p = Path(path)
    ensure_dir(p.parent)
    if normalize:
        text = normalize_newlines(text)
    # Write to a temp file in the same directory then replace atomically.
    fd, tmp_name = tempfile.mkstemp(prefix=p.name + ".", suffix=".tmp", dir=str(p.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding=encoding, newline="\n") as f:
            f.write(text)
            f.flush()
            if fsync:
                os.fsync(f.fileno())
        os.replace(str(tmp_path), str(p))
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
def atomic_write_json(
    path: PathLike,
    obj: Any,
    *,
    encoding: str = "utf-8",
    normalize: bool = True,
    fsync: bool = True,
) -> None:
    text = stable_json_dumps(obj) + "\n"
    atomic_write_text(path, text, encoding=encoding, normalize=normalize, fsync=fsync)
def mapping_fingerprint(
    named_texts: Dict[str, str],
    *,
    normalize: bool = True,
    encoding: str = "utf-8",
) -> str:
    # Deterministic overall fingerprint for a set of named markdown outputs.
    items = []
    for k in sorted(named_texts.keys()):
        items.append((k, content_hash(named_texts[k], normalize=normalize, encoding=encoding)))
    payload = stable_json_dumps(items)
    return content_hash(payload, normalize=False, encoding=encoding)
