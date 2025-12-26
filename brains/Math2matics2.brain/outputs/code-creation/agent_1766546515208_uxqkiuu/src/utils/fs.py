"""Filesystem utilities.

These helpers are intentionally small and deterministic: they create directories
as needed and write files atomically (write-to-temp then replace) so downstream
artifact generation is reproducible and robust against partial writes.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Union


PathLike = Union[str, os.PathLike, Path]

__all__ = [
    "ensure_dir",
    "ensure_parent_dir",
    "atomic_write_text",
    "atomic_write_bytes",
]
def ensure_dir(path: PathLike) -> Path:
    """Create *path* as a directory if it does not exist and return it."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def ensure_parent_dir(path: PathLike) -> Path:
    """Create the parent directory for *path* if needed and return the parent."""
    p = Path(path)
    parent = p if p.suffix == "" and p.name != "" and p.exists() and p.is_dir() else p.parent
    parent.mkdir(parents=True, exist_ok=True)
    return parent
def _atomic_replace(tmp_path: Path, final_path: Path) -> None:
    """Replace *final_path* with *tmp_path* atomically (best effort across platforms)."""
    # os.replace is atomic on POSIX and Windows when source/dest are on same filesystem.
    os.replace(str(tmp_path), str(final_path))


def atomic_write_bytes(path: PathLike, data: bytes) -> Path:
    """Atomically write bytes to *path* and return the final Path."""
    final_path = Path(path)
    ensure_parent_dir(final_path)

    # Use a temp file in the same directory to ensure os.replace is atomic.
    fd = None
    tmp_path = None
    try:
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{final_path.name}.",
            suffix=".tmp",
            dir=str(final_path.parent),
        )
        tmp_path = Path(tmp_name)
        with os.fdopen(fd, "wb") as f:
            fd = None  # fd is now managed by the file object
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        _atomic_replace(tmp_path, final_path)

        # Best-effort directory fsync for durability on POSIX.
        if hasattr(os, "O_DIRECTORY"):
            try:
                dfd = os.open(str(final_path.parent), os.O_DIRECTORY)
                try:
                    os.fsync(dfd)
                finally:
                    os.close(dfd)
            except OSError:
                pass
        return final_path
    finally:
        # Clean up on failure.
        try:
            if fd is not None:
                os.close(fd)
        except OSError:
            pass
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def atomic_write_text(
    path: PathLike,
    text: str,
    *,
    encoding: str = "utf-8",
    newline: str = "
",
) -> Path:
    """Atomically write text to *path* using a stable newline convention.

    Note: newline normalization here avoids platform-dependent output deltas.
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if newline != "\n":
        normalized = normalized.replace("\n", newline)
    return atomic_write_bytes(Path(path), normalized.encode(encoding))
