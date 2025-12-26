from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any, Union, Optional


def _resolve_output_dir() -> Path:
    raw = os.getenv("OUTPUT_DIR", "./outputs")
    p = Path(raw).expanduser()
    try:
        return p.resolve()
    except FileNotFoundError:
        # For non-existent relative paths, resolve against current working directory.
        return (Path.cwd() / p).resolve()


OUTPUT_DIR: Path = _resolve_output_dir()

PathLike = Union[str, os.PathLike, Path]


def ensure_dir(path: PathLike) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _as_path(path: PathLike) -> Path:
    return path if isinstance(path, Path) else Path(path)


def write_text(
    path: PathLike,
    text: str,
    *,
    encoding: str = "utf-8",
    newline: str = "\n",
) -> Path:
    p = _as_path(path)
    ensure_dir(p.parent)
    data = text.replace("\r\n", "\n").replace("\r", "\n")
    if newline != "\n":
        data = data.replace("\n", newline)
    if not data.endswith(newline) and data != "":
        data += newline
    p.write_text(data, encoding=encoding)
    return p


def write_json(
    path: PathLike,
    obj: Any,
    *,
    indent: int = 2,
    sort_keys: bool = True,
    ensure_ascii: bool = False,
) -> Path:
    text = json.dumps(obj, indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii)
    return write_text(path, text)


__all__ = ["OUTPUT_DIR", "ensure_dir", "write_text", "write_json"]
