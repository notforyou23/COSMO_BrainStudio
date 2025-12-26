"""refactor_modularize.utils

Small, dependency-light helpers shared across the refactoring pipeline:
filesystem convenience, text normalization, and simple validations.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
import hashlib
import os
import re
import unicodedata
# ----------------------------- Filesystem helpers -----------------------------


def ensure_dir(path: Path) -> Path:
    """Create *path* (a directory) if it doesn't exist and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_text(path: Path, encoding: str = "utf-8") -> str:
    """Read a UTF-8 (by default) text file."""
    return path.read_text(encoding=encoding)


def write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Write text to *path*, creating parent directories as needed."""
    ensure_dir(path.parent)
    path.write_text(text, encoding=encoding)


def list_files(root: Path, pattern: str = "*") -> list[Path]:
    """Return sorted files under *root* matching *pattern* (non-recursive)."""
    return sorted(p for p in root.glob(pattern) if p.is_file())


def safe_relpath(path: Path, root: Path) -> str:
    """Return POSIX relative path; if unrelated, fall back to filename."""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return path.name
# ------------------------------ Text utilities -------------------------------


_NEWLINE_RE = re.compile(r"\r\n?|\n")


def normalize_newlines(text: str, newline: str = "\n") -> str:
    """Normalize CRLF/CR newlines to *newline* (default: \n)."""
    return _NEWLINE_RE.sub(newline, text)


def strip_trailing_whitespace(text: str) -> str:
    """Strip trailing spaces/tabs on each line (preserves line count)."""
    return "\n".join(line.rstrip(" \t") for line in normalize_newlines(text).split("\n"))


def stable_hash(text: str) -> str:
    """Short, stable content hash used for deterministic naming."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


_SLUG_SEP_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str, max_len: int = 80) -> str:
    """Convert *value* to a filesystem-friendly slug."""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = value.lower().strip()
    value = _SLUG_SEP_RE.sub("-", value).strip("-")
    if not value:
        value = "item"
    return value[:max_len].rstrip("-")
# ------------------------------- Validations --------------------------------


_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ValidationError(ValueError):
    """Raised when an input does not satisfy expected constraints."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def validate_identifier(name: str, *, what: str = "identifier") -> str:
    """Validate Python identifier-ish names used in generated modules."""
    require(bool(name), f"{what} is empty")
    require(bool(_IDENT_RE.match(name)), f"invalid {what}: {name!r}")
    return name


def require_keys(mapping: Mapping[str, Any], keys: Sequence[str], *, what: str = "mapping") -> None:
    missing = [k for k in keys if k not in mapping]
    require(not missing, f"{what} missing keys: {', '.join(missing)}")


def within_root(path: Path, root: Path) -> bool:
    """True if *path* resolves under *root* (prevents path traversal)."""
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


def atomic_write(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Best-effort atomic write: write to temp file then replace."""
    ensure_dir(path.parent)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(text, encoding=encoding)
    os.replace(tmp, path)
