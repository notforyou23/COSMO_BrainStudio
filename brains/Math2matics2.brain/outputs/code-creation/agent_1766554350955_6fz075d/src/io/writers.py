from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Iterable, Optional, Union

PathLike = Union[str, Path]


def _import_output_dir_helper() -> Optional[callable]:
    try:
        from src.utils.output_path import get_output_dir as _get_output_dir  # type: ignore
        return _get_output_dir
    except Exception:
        return None


def get_output_dir() -> Path:
    """Single output directory helper.

    Uses src.utils.output_path.get_output_dir when available; otherwise falls back
    to $OUTPUT_DIR or ./outputs (relative path).
    """
    helper = _import_output_dir_helper()
    if helper is not None:
        p = Path(helper())
        return p

    env = (os.environ.get("OUTPUT_DIR") or "").strip()
    p = Path(env) if env else Path("outputs")
    return p


def output_path(*parts: PathLike, mkdir: bool = True) -> Path:
    """Build an artifact/log destination under OUTPUT_DIR."""
    base = get_output_dir()
    p = base.joinpath(*[str(x) for x in parts]) if parts else base
    if mkdir:
        p.parent.mkdir(parents=True, exist_ok=True)
    return p


def write_text(rel_path: PathLike, text: str, encoding: str = "utf-8") -> Path:
    p = output_path(rel_path)
    p.write_text(text, encoding=encoding)
    return p


def write_lines(rel_path: PathLike, lines: Iterable[str], encoding: str = "utf-8") -> Path:
    p = output_path(rel_path)
    p.write_text("\n".join(lines) + "\n", encoding=encoding)
    return p


def write_json(
    rel_path: PathLike,
    obj: Any,
    *,
    indent: int = 2,
    sort_keys: bool = True,
    ensure_ascii: bool = False,
) -> Path:
    p = output_path(rel_path)
    p.write_text(
        json.dumps(obj, indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii) + "\n",
        encoding="utf-8",
    )
    return p


def write_bytes(rel_path: PathLike, data: bytes) -> Path:
    p = output_path(rel_path)
    p.write_bytes(data)
    return p


def write_log(rel_path: PathLike, message: str, *, append: bool = True, encoding: str = "utf-8") -> Path:
    """Write a log line to a file under OUTPUT_DIR, avoiding absolute /outputs paths."""
    p = output_path(rel_path)
    mode = "a" if append else "w"
    with p.open(mode, encoding=encoding) as f:
        f.write(message.rstrip("\n") + "\n")
    return p


def ensure_artifact_dir(rel_dir: PathLike) -> Path:
    p = output_path(rel_dir, mkdir=False)
    p.mkdir(parents=True, exist_ok=True)
    return p
