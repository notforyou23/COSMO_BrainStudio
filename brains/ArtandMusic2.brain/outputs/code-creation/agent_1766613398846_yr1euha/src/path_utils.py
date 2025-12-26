from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Union

PathLike = Union[str, Path]


class PathSafetyError(ValueError):
    """Raised when a requested path would escape the configured project root."""


def _as_path(p: PathLike) -> Path:
    return p if isinstance(p, Path) else Path(p)


def normalize_root(root: PathLike) -> Path:
    """Return an absolute, resolved root path (without requiring it to exist)."""
    return _as_path(root).expanduser().resolve(strict=False)
def resolve_under_root(root: PathLike, candidate: PathLike) -> Path:
    """Resolve candidate path under root, rejecting any escape attempts.

    - If candidate is relative, it is joined to root.
    - If candidate is absolute, it must already be within root.
    """
    root_p = normalize_root(root)
    cand_p = _as_path(candidate).expanduser()
    combined = cand_p if cand_p.is_absolute() else root_p / cand_p
    resolved = combined.resolve(strict=False)

    try:
        resolved.relative_to(root_p)
    except Exception as e:
        raise PathSafetyError(f"Path escapes root: {resolved} (root={root_p})") from e
    return resolved


def safe_join(root: PathLike, *parts: PathLike) -> Path:
    p = Path()
    for part in parts:
        p = p / _as_path(part)
    return resolve_under_root(root, p)


def rel_to_root(root: PathLike, path: PathLike) -> str:
    """Return a POSIX-style relative path for display/logging."""
    root_p = normalize_root(root)
    path_p = resolve_under_root(root_p, path)
    return path_p.relative_to(root_p).as_posix()
@dataclass(frozen=True)
class FSContext:
    """Filesystem context enforcing a project root and optional dry-run behavior."""

    root: Path
    dry_run: bool = False

    @classmethod
    def from_root(cls, root: PathLike, dry_run: bool = False) -> "FSContext":
        return cls(root=normalize_root(root), dry_run=bool(dry_run))

    def resolve(self, path: PathLike) -> Path:
        return resolve_under_root(self.root, path)

    def join(self, *parts: PathLike) -> Path:
        return safe_join(self.root, *parts)

    def ensure_dir(self, path: PathLike) -> Path:
        p = self.resolve(path)
        if not self.dry_run:
            p.mkdir(parents=True, exist_ok=True)
        return p

    def write_text(
        self,
        path: PathLike,
        text: str,
        *,
        encoding: str = "utf-8",
        newline: Optional[str] = "\n",
        mkdirs: bool = True,
        overwrite: bool = True,
    ) -> Path:
        p = self.resolve(path)
        if mkdirs:
            self.ensure_dir(p.parent)
        if self.dry_run:
            return p
        if (not overwrite) and p.exists():
            return p
        data = text.replace("\r\n", "\n").replace("\r", "\n")
        if newline is not None:
            data = data.replace("\n", newline)
        p.write_text(data, encoding=encoding)
        return p

    def write_bytes(
        self,
        path: PathLike,
        data: bytes,
        *,
        mkdirs: bool = True,
        overwrite: bool = True,
    ) -> Path:
        p = self.resolve(path)
        if mkdirs:
            self.ensure_dir(p.parent)
        if self.dry_run:
            return p
        if (not overwrite) and p.exists():
            return p
        p.write_bytes(data)
        return p
def list_files(root: PathLike, subdir: PathLike = ".") -> Iterable[Path]:
    """Yield files under root/subdir (non-recursive) with safety enforcement."""
    root_p = normalize_root(root)
    dir_p = resolve_under_root(root_p, subdir)
    if not dir_p.exists() or not dir_p.is_dir():
        return ()
    return tuple(p for p in dir_p.iterdir() if p.is_file())


def is_within_root(root: PathLike, path: PathLike) -> bool:
    try:
        resolve_under_root(root, path)
        return True
    except PathSafetyError:
        return False
