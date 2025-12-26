"""I/O utilities for deterministic artifact generation.

Provides small helpers to create output directories and write files in a way that
is stable for diffs (normalized newlines) and safe against partial writes
(atomic replace).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
import tempfile
from typing import Any, Optional
def ensure_dir(path: Path) -> Path:
    """Create *path* as a directory (including parents) and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path
def normalize_newlines(text: str, newline: str = "\n") -> str:
    """Normalize CRLF/CR newlines to *newline* for stable diffs."""
    if not text:
        return ""
    # Replace CRLF first, then any remaining CR.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if newline != "\n":
        text = text.replace("\n", newline)
    return text
def _atomic_replace(target: Path, tmp_path: Path) -> None:
    """Replace *target* with *tmp_path* atomically where supported."""
    # os.replace is atomic on POSIX and Windows when source/target are on same fs.
    os.replace(str(tmp_path), str(target))
def atomic_write_bytes(target: Path, data: bytes) -> None:
    """Atomically write bytes to *target*, creating parent directories."""
    target = Path(target)
    ensure_dir(target.parent)
    fd, tmp_name = tempfile.mkstemp(prefix=target.name + ".", dir=str(target.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        _atomic_replace(target, tmp_path)
    finally:
        # If replace failed, clean up the temp file.
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
def atomic_write_text(
    target: Path,
    text: str,
    *,
    encoding: str = "utf-8",
    newline: str = "\n",
    ensure_trailing_newline: bool = True,
) -> None:
    """Atomically write text to *target* with normalized line endings."""
    text = normalize_newlines(text, newline=newline)
    if ensure_trailing_newline and text and not text.endswith(newline):
        text += newline
    atomic_write_bytes(target, text.encode(encoding))
@dataclass(frozen=True)
class JsonWriteOptions:
    sort_keys: bool = True
    indent: int = 2
    ensure_ascii: bool = False
def atomic_write_json(
    target: Path,
    obj: Any,
    *,
    opts: Optional[JsonWriteOptions] = None,
    newline: str = "\n",
) -> None:
    """Serialize *obj* to JSON deterministically and atomically write it."""
    options = opts or JsonWriteOptions()
    text = json.dumps(
        obj,
        sort_keys=options.sort_keys,
        indent=options.indent,
        ensure_ascii=options.ensure_ascii,
    )
    atomic_write_text(target, text, newline=newline)
