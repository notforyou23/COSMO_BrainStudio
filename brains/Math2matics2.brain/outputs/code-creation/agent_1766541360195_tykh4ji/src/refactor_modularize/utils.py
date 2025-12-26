"""Shared utilities used across refactor_modularize.

Includes helpers for path handling, hashing (sha256), text diffing, and
safe file IO with atomic writes.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Union

import difflib
import hashlib
import os
import tempfile
PathLike = Union[str, os.PathLike, Path]
def to_path(p: PathLike) -> Path:
    """Convert a path-like into a Path (does not require existence)."""
    return p if isinstance(p, Path) else Path(p)


def ensure_parent_dir(path: PathLike) -> Path:
    """Ensure `path` parent directory exists; return `path` as Path."""
    p = to_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def relpath(path: PathLike, start: PathLike) -> str:
    """Return a stable forward-slash relative path (best-effort)."""
    p, s = to_path(path), to_path(start)
    try:
        r = p.relative_to(s)
    except Exception:
        r = Path(os.path.relpath(os.fspath(p), os.fspath(s)))
    return r.as_posix()
def normalize_newlines(text: str) -> str:
    """Normalize CRLF/CR newlines to LF."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def read_text(path: PathLike, encoding: str = "utf-8") -> str:
    """Read a text file; normalizes newlines to LF."""
    return normalize_newlines(to_path(path).read_text(encoding=encoding))


def write_text_atomic(
    path: PathLike,
    text: str,
    *,
    encoding: str = "utf-8",
    newline: str = "\n",
) -> None:
    """Atomically write text to `path` (temp file then os.replace)."""
    p = ensure_parent_dir(path)
    data = normalize_newlines(text)
    if newline != "\n":
        data = data.replace("\n", newline)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding=encoding,
        dir=os.fspath(p.parent),
        prefix=f".{p.name}.",
        suffix=".tmp",
        delete=False,
        newline="",
    ) as tf:
        tmp_name = tf.name
        tf.write(data)
    os.replace(tmp_name, os.fspath(p))
def sha256_bytes(data: bytes) -> str:
    """Hex sha256 for raw bytes."""
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str, encoding: str = "utf-8") -> str:
    """Hex sha256 for text (after newline normalization)."""
    return sha256_bytes(normalize_newlines(text).encode(encoding))


def sha256_file(path: PathLike, chunk_size: int = 1024 * 1024) -> str:
    """Hex sha256 of a file (binary read)."""
    h = hashlib.sha256()
    with open(os.fspath(to_path(path)), "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()
def unified_diff(
    a_text: str,
    b_text: str,
    *,
    fromfile: str = "a",
    tofile: str = "b",
    lineterm: str = "\n",
) -> str:
    """Return a unified diff string between two texts (newline-normalized)."""
    a_lines = normalize_newlines(a_text).splitlines(keepends=True)
    b_lines = normalize_newlines(b_text).splitlines(keepends=True)
    d = difflib.unified_diff(a_lines, b_lines, fromfile=fromfile, tofile=tofile, lineterm=lineterm)
    return "".join(d)
@dataclass(frozen=True)
class FileSnapshot:
    """Immutable representation of file content and a content hash."""
    path: Path
    text: str
    sha256: str

    @classmethod
    def from_path(cls, path: PathLike, encoding: str = "utf-8") -> "FileSnapshot":
        p = to_path(path)
        t = read_text(p, encoding=encoding)
        return cls(path=p, text=t, sha256=sha256_text(t, encoding=encoding))
