"""refactor_modularize.utils

Small, reusable helpers used by artifact-generation scripts.

Focus: filesystem IO, JSON/text convenience, hashing, logging setup, and tiny
pipeline helpers. The module is intentionally dependency-free and stable.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, MutableMapping, Optional, Sequence, Tuple
import hashlib
import json
import logging
import os
import re
import tempfile
from datetime import datetime, timezone
# ---------------------------
# Filesystem + text utilities
# ---------------------------

def ensure_dir(path: Path) -> Path:
    """Create *path* as a directory (parents=True). Returns the same path."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_text(path: Path, *, encoding: str = "utf-8") -> str:
    """Read a UTF-8 (by default) text file."""
    return path.read_text(encoding=encoding)


def write_text(path: Path, text: str, *, encoding: str = "utf-8") -> Path:
    """Write text to *path*, creating parent directories."""
    ensure_dir(path.parent)
    path.write_text(text, encoding=encoding)
    return path


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> Path:
    """Atomically write text by writing to a temp file and os.replace()."""
    ensure_dir(path.parent)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
    return path
# -------------
# JSON utilities
# -------------

def read_json(path: Path, *, encoding: str = "utf-8") -> Any:
    """Read JSON from a file."""
    return json.loads(read_text(path, encoding=encoding))


def write_json(
    path: Path,
    data: Any,
    *,
    encoding: str = "utf-8",
    indent: int = 2,
    sort_keys: bool = True,
    ensure_ascii: bool = False,
) -> Path:
    """Write JSON with stable defaults suitable for diffs."""
    text = json.dumps(data, indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii) + "\n"
    return atomic_write_text(path, text, encoding=encoding)
# ----------------
# Hashing utilities
# ----------------

def sha256_bytes(data: bytes) -> str:
    """Return hex sha256 of *data*."""
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str, *, encoding: str = "utf-8") -> str:
    """Return hex sha256 of *text*."""
    return sha256_bytes(text.encode(encoding))


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Return hex sha256 of a file without loading it all into memory."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()
# ----------------
# Text + timestamps
# ----------------

_slug_re = re.compile(r"[^a-z0-9]+", re.IGNORECASE)

def slugify(value: str, *, max_len: int = 80) -> str:
    """Make a filesystem-friendly slug (lowercase, dash-separated)."""
    v = _slug_re.sub("-", value.strip().lower()).strip("-")
    return v[:max_len] if max_len and len(v) > max_len else v


def now_utc_iso() -> str:
    """UTC timestamp in ISO-8601 with milliseconds (Z suffix)."""
    dt = datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H-%M-%S-%f")[:-3] + "Z"  # safe for filenames
# ----------------
# Logging utilities
# ----------------

def configure_logger(name: str = "refactor_modularize", *, level: int = logging.INFO) -> logging.Logger:
    """Return a logger with a simple, idempotent StreamHandler."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        logger.addHandler(h)
    logger.propagate = False
    return logger
# ----------------
# Tiny pipeline helpers
# ----------------

@dataclass(frozen=True)
class StepResult:
    """Result for a pipeline step."""
    name: str
    ok: bool
    detail: str = ""


def run_steps(
    steps: Sequence[Tuple[str, Callable[[], Any]]],
    *,
    logger: Optional[logging.Logger] = None,
    stop_on_error: bool = True,
) -> Sequence[StepResult]:
    """Run (name, callable) steps with optional logging and error handling."""
    log = logger or logging.getLogger("refactor_modularize")
    results: list[StepResult] = []
    for name, fn in steps:
        try:
            fn()
            results.append(StepResult(name=name, ok=True))
            log.debug("step ok: %s", name)
        except Exception as e:  # pragma: no cover (script utility)
            results.append(StepResult(name=name, ok=False, detail=str(e)))
            log.error("step failed: %s: %s", name, e)
            if stop_on_error:
                break
    return results
