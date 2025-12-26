"""Shared filesystem utilities for canonicalization pipeline.

Provides safe directory creation, atomic writes, copy/move helpers,
checksum calculation, and dry-run support.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import os
import shutil
import tempfile
from typing import Optional, Union

PathLike = Union[str, os.PathLike, Path]


@dataclass(frozen=True)
class FSContext:
    dry_run: bool = False

    def log(self, msg: str) -> None:
        # Intentionally minimal; callers can override/log externally.
        return
def ensure_dir(path: PathLike, ctx: FSContext = FSContext()) -> Path:
    p = Path(path)
    if ctx.dry_run:
        return p
    p.mkdir(parents=True, exist_ok=True)
    return p


def sha256_file(path: PathLike, chunk_size: int = 1024 * 1024) -> str:
    p = Path(path)
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_write_bytes(path: PathLike, data: bytes, ctx: FSContext = FSContext(), mode: Optional[int] = None) -> Path:
    p = Path(path)
    ensure_dir(p.parent, ctx=ctx)
    if ctx.dry_run:
        return p
    fd, tmp_name = tempfile.mkstemp(prefix=p.name + ".", suffix=".tmp", dir=str(p.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        if mode is not None:
            os.chmod(tmp, mode)
        os.replace(tmp, p)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
    return p


def atomic_write_text(path: PathLike, text: str, ctx: FSContext = FSContext(), encoding: str = "utf-8", mode: Optional[int] = None) -> Path:
    return atomic_write_bytes(path, text.encode(encoding), ctx=ctx, mode=mode)
def copy_file(src: PathLike, dst: PathLike, ctx: FSContext = FSContext(), overwrite: bool = False, preserve_metadata: bool = True) -> Path:
    s, d = Path(src), Path(dst)
    if not s.is_file():
        raise FileNotFoundError(str(s))
    ensure_dir(d.parent, ctx=ctx)
    if d.exists() and not overwrite:
        raise FileExistsError(str(d))
    if ctx.dry_run:
        return d
    if preserve_metadata:
        shutil.copy2(s, d)
    else:
        shutil.copyfile(s, d)
    return d


def move_file(src: PathLike, dst: PathLike, ctx: FSContext = FSContext(), overwrite: bool = False) -> Path:
    s, d = Path(src), Path(dst)
    if not s.exists():
        raise FileNotFoundError(str(s))
    ensure_dir(d.parent, ctx=ctx)
    if d.exists() and not overwrite:
        raise FileExistsError(str(d))
    if ctx.dry_run:
        return d
    try:
        os.replace(s, d)  # atomic when same filesystem
    except OSError:
        shutil.move(str(s), str(d))
    return d


def remove_path(path: PathLike, ctx: FSContext = FSContext(), missing_ok: bool = True) -> None:
    p = Path(path)
    if not p.exists():
        if missing_ok:
            return
        raise FileNotFoundError(str(p))
    if ctx.dry_run:
        return
    if p.is_dir() and not p.is_symlink():
        shutil.rmtree(p)
    else:
        p.unlink()


def same_content(a: PathLike, b: PathLike) -> bool:
    pa, pb = Path(a), Path(b)
    if not (pa.is_file() and pb.is_file()):
        return False
    try:
        if pa.stat().st_size != pb.stat().st_size:
            return False
    except OSError:
        return False
    return sha256_file(pa) == sha256_file(pb)
