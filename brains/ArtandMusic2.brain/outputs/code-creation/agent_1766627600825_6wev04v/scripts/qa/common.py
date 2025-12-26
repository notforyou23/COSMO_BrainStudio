from __future__ import annotations

from pathlib import Path
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Union

# Repository root = .../scripts/qa/common.py -> parents[2]
ROOT_DIR = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT_DIR / "scripts"
OUTPUTS_DIR = ROOT_DIR / "outputs"
QA_DIR = OUTPUTS_DIR / "qa"
LOGS_DIR = QA_DIR / "logs"

UTF8 = "utf-8"
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")

PathLike = Union[str, os.PathLike, Path]


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S-%fZ")


def ensure_dir(p: PathLike) -> Path:
    path = Path(p)
    path.mkdir(parents=True, exist_ok=True)
    return path


def canonical_path(p: PathLike, *, base: Optional[PathLike] = None) -> Path:
    path = Path(p)
    if base is not None:
        b = Path(base)
        path = path if path.is_absolute() else (b / path)
    try:
        return path.resolve()
    except FileNotFoundError:
        # resolve(strict=False) isn't available on older Pythons in some contexts
        return (path.parent.resolve() / path.name) if path.parent.exists() else path.absolute()


def is_within(path: PathLike, root: PathLike) -> bool:
    p = canonical_path(path)
    r = canonical_path(root)
    try:
        p.relative_to(r)
        return True
    except Exception:
        return False


def require_within(path: PathLike, root: PathLike, *, label: str = "path") -> Path:
    p = canonical_path(path)
    r = canonical_path(root)
    if not is_within(p, r):
        raise ValueError(f"{label} must be within {r}: {p}")
    return p


def safe_filename(name: str, *, max_len: int = 200, default: str = "artifact") -> str:
    s = (name or "").strip()
    s = _SAFE_NAME_RE.sub("_", s)
    s = s.strip("._-") or default
    return s[:max_len]


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    ensure_dir(path.parent)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def atomic_write_text(path: PathLike, text: str, *, encoding: str = UTF8) -> Path:
    p = Path(path)
    _atomic_write_bytes(p, text.encode(encoding, errors="replace"))
    return p


def atomic_write_json(path: PathLike, obj: Any, *, indent: int = 2, sort_keys: bool = True) -> Path:
    p = Path(path)
    txt = json.dumps(obj, indent=indent, sort_keys=sort_keys, ensure_ascii=False) + "\n"
    return atomic_write_text(p, txt, encoding=UTF8)


def append_text(path: PathLike, text: str, *, encoding: str = UTF8) -> Path:
    p = Path(path)
    ensure_dir(p.parent)
    with open(p, "a", encoding=encoding, errors="replace") as f:
        f.write(text)
    return p


def write_log(name: str, content: Union[str, bytes], *, subdir: Optional[str] = None) -> Path:
    base = LOGS_DIR if subdir is None else (LOGS_DIR / safe_filename(subdir))
    ensure_dir(base)
    fname = safe_filename(name)
    p = base / fname
    if isinstance(content, bytes):
        _atomic_write_bytes(p, content)
    else:
        atomic_write_text(p, content)
    return p


def log_path(name: str, *, subdir: Optional[str] = None) -> Path:
    base = LOGS_DIR if subdir is None else (LOGS_DIR / safe_filename(subdir))
    ensure_dir(base)
    return base / safe_filename(name)


def human_kv(items: Mapping[str, Any]) -> str:
    lines = []
    for k in sorted(items.keys()):
        v = items[k]
        if isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False)
        lines.append(f"{k}: {v}")
    return "\n".join(lines) + ("\n" if lines else "")
