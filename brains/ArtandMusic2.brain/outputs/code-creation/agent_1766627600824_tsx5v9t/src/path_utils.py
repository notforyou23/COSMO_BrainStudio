from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Union
import os


class PathUtilsError(ValueError):
    """Raised when a path fails safety or resolution checks."""


def _resolve(p: Path, strict: bool = False) -> Path:
    try:
        return p.expanduser().resolve(strict=strict)
    except FileNotFoundError:
        return p.expanduser().absolute()


def _is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except Exception:
        return False


def _commonpath_is_within(child: Path, parent: Path) -> bool:
    # Fallback for edge cases (mixed absolute/relative, symlinks) using commonpath.
    try:
        return os.path.commonpath([str(child), str(parent)]) == str(parent)
    except Exception:
        return False


def ensure_within_root(path: Union[str, Path], root: Union[str, Path], *, strict: bool = False) -> Path:
    """Resolve `path` and verify it lies within resolved `root`. Returns resolved path."""
    r = _resolve(Path(root), strict=strict)
    p = _resolve(Path(path), strict=strict)
    if _is_relative_to(p, r) or _commonpath_is_within(p, r):
        return p
    raise PathUtilsError(f"Path escapes root: path={p} root={r}")


def safe_join(root: Union[str, Path], *parts: Union[str, Path], strict: bool = False) -> Path:
    """Join parts to root, resolve, and ensure result stays within root."""
    r = _resolve(Path(root), strict=strict)
    joined = r.joinpath(*map(str, parts))
    return ensure_within_root(joined, r, strict=strict)


def find_project_root(
    start: Optional[Union[str, Path]] = None,
    *,
    markers: Iterable[str] = ("pyproject.toml", ".git", "setup.cfg", "requirements.txt"),
    strict: bool = False,
) -> Path:
    """Walk upward from `start` to find a directory containing any marker; else returns start dir."""
    s = Path(start) if start is not None else Path.cwd()
    s = _resolve(s, strict=strict)
    cur = s if s.is_dir() else s.parent
    for d in (cur, *cur.parents):
        for m in markers:
            if d.joinpath(m).exists():
                return d
    return cur


def resolve_from_root(
    rel: Union[str, Path],
    *,
    root: Optional[Union[str, Path]] = None,
    start: Optional[Union[str, Path]] = None,
    strict: bool = False,
) -> Path:
    """Resolve a repo-root-relative path safely (prevents '..' escapes)."""
    r = Path(root) if root is not None else find_project_root(start=start, strict=strict)
    if Path(rel).is_absolute():
        return ensure_within_root(rel, r, strict=strict)
    return safe_join(r, rel, strict=strict)


@dataclass(frozen=True)
class RootedPath:
    """A helper that pins operations to a fixed project root."""
    root: Path

    @classmethod
    def from_start(
        cls,
        start: Optional[Union[str, Path]] = None,
        *,
        markers: Iterable[str] = ("pyproject.toml", ".git", "setup.cfg", "requirements.txt"),
        strict: bool = False,
    ) -> "RootedPath":
        return cls(find_project_root(start=start, markers=markers, strict=strict))

    def resolve(self, rel: Union[str, Path], *, strict: bool = False) -> Path:
        return resolve_from_root(rel, root=self.root, strict=strict)

    def join(self, *parts: Union[str, Path], strict: bool = False) -> Path:
        return safe_join(self.root, *parts, strict=strict)

    def ensure(self, path: Union[str, Path], *, strict: bool = False) -> Path:
        return ensure_within_root(path, self.root, strict=strict)
