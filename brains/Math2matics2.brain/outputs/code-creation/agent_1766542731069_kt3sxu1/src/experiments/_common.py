"""Shared helpers for the :mod:`experiments` package.

The project keeps these utilities small and dependency-free so they can be
imported by I/O, sweep, and plotting modules without introducing heavy imports.
"""

from __future__ import annotations

from dataclasses import is_dataclass, asdict
from pathlib import Path
from typing import Any, Iterable, Mapping, MutableMapping, Sequence, TypeVar, Union, overload

PathLike = Union[str, Path]
T = TypeVar("T")

__all__ = [
    "PathLike",
    "as_path",
    "ensure_dir",
    "ensure_parent_dir",
    "ensure_suffix",
    "require",
    "check_one_of",
    "jsonable",
]
@overload
def as_path(path: None) -> None: ...
@overload
def as_path(path: PathLike) -> Path: ...


def as_path(path: PathLike | None) -> Path | None:
    """Coerce a path-like value to :class:`~pathlib.Path`.

    Returns ``None`` if ``path`` is ``None``.
    """
    if path is None:
        return None
    return path if isinstance(path, Path) else Path(path)
def ensure_dir(path: PathLike) -> Path:
    """Ensure a directory exists and return it as a :class:`~pathlib.Path`."""
    p = as_path(path)
    assert p is not None
    p.mkdir(parents=True, exist_ok=True)
    return p


def ensure_parent_dir(file_path: PathLike) -> Path:
    """Ensure the parent directory of a file exists; return the file path."""
    p = as_path(file_path)
    assert p is not None
    if p.parent != p:
        p.parent.mkdir(parents=True, exist_ok=True)
    return p


def ensure_suffix(path: PathLike, suffix: str) -> Path:
    """Return *path* as a :class:`~pathlib.Path` with the given suffix.

    ``suffix`` may be provided with or without a leading dot.
    """
    p = as_path(path)
    assert p is not None
    suf = suffix if suffix.startswith(".") else f".{suffix}"
    return p if p.suffix == suf else p.with_suffix(suf)
def require(condition: bool, message: str, exc: type[Exception] = ValueError) -> None:
    """Raise *exc* with *message* if *condition* is falsy."""
    if not condition:
        raise exc(message)


def check_one_of(name: str, value: Any, options: Iterable[Any]) -> Any:
    """Validate that ``value`` is in ``options`` and return it."""
    opts = tuple(options)
    if value not in opts:
        raise ValueError(f"{name} must be one of {opts!r}; got {value!r}")
    return value
def jsonable(obj: Any) -> Any:
    """Convert common Python objects into JSON-serializable structures.

    This is intended for metadata/config persistence and errs on the side of
    preserving information (e.g., converting :class:`~pathlib.Path` to ``str``).
    """
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, Path):
        return str(obj)
    if is_dataclass(obj):
        return {k: jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, Mapping):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, set):
        return sorted(jsonable(v) for v in obj)
    # Numpy scalars / pandas types often define ``item``.
    item = getattr(obj, "item", None)
    if callable(item):
        try:
            return jsonable(item())
        except Exception:
            pass
    # Fall back to string representation (safe for logs/metadata).
    return str(obj)
