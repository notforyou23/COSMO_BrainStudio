"""Unified experiment IO utilities.

Provides a small, dependency-light layer for consistent paths and safe
read/write of configs, results, artifacts, and tabular data.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import csv
import io
import json
import os
import tempfile
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Union


Json = Union[Dict[str, Any], List[Any], str, int, float, bool, None]
def _norm_rel(*parts: Union[str, os.PathLike]) -> Path:
    p = Path(*parts)
    if p.is_absolute():
        raise ValueError(f"absolute paths not allowed: {p}")
    # Prevent traversal: any '..' segment is rejected.
    if any(seg == ".." for seg in p.parts):
        raise ValueError(f"path traversal not allowed: {p}")
    return p


def safe_join(root: Union[str, os.PathLike], *parts: Union[str, os.PathLike]) -> Path:
    """Join *parts under root, rejecting absolute/traversing paths."""
    root_p = Path(root)
    rel = _norm_rel(*parts)
    out = (root_p / rel).resolve()
    root_r = root_p.resolve()
    try:
        out.relative_to(root_r)
    except Exception as e:  # pragma: no cover
        raise ValueError(f"path escapes root: {out}") from e
    return out


def ensure_dir(path: Union[str, os.PathLike]) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def atomic_write(path: Union[str, os.PathLike], data: bytes) -> Path:
    """Atomic write to path (best-effort on the current filesystem)."""
    p = Path(path)
    ensure_dir(p.parent)
    fd, tmp = tempfile.mkstemp(prefix=p.name + ".", dir=str(p.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
    return p
def read_text(path: Union[str, os.PathLike], encoding: str = "utf-8") -> str:
    return Path(path).read_text(encoding=encoding)


def write_text(path: Union[str, os.PathLike], text: str, encoding: str = "utf-8") -> Path:
    return atomic_write(path, text.encode(encoding))


def read_json(path: Union[str, os.PathLike]) -> Json:
    return json.loads(read_text(path))


def write_json(
    path: Union[str, os.PathLike],
    obj: Json,
    *,
    indent: int = 2,
    sort_keys: bool = True,
) -> Path:
    text = json.dumps(obj, indent=indent, sort_keys=sort_keys, ensure_ascii=False) + "\n"
    return write_text(path, text)
def write_table(
    path: Union[str, os.PathLike],
    rows: Iterable[Mapping[str, Any]],
    *,
    fieldnames: Optional[Sequence[str]] = None,
    dialect: str = "excel",
) -> Path:
    """Write list/iterable of dict rows to CSV.

    If fieldnames is omitted, it is inferred from the first row.
    """
    it = iter(rows)
    first = next(it, None)
    if first is None:
        raise ValueError("cannot write empty table (no rows)")
    if fieldnames is None:
        fieldnames = list(first.keys())
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames, dialect=dialect)
    w.writeheader()
    w.writerow(dict(first))
    for r in it:
        w.writerow(dict(r))
    return write_text(path, buf.getvalue())


def read_table(path: Union[str, os.PathLike], *, dialect: str = "excel") -> List[Dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, dialect=dialect))
@dataclass(frozen=True)
class ExperimentIO:
    """Consistent filesystem layout for experiments.

    Layout under root:
      - configs/   : configuration files (json)
      - results/   : results/metrics (json, csv)
      - artifacts/ : arbitrary files (binary/text)
      - tables/    : tabular exports (csv)
    """

    root: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", Path(self.root))

    def _dir(self, name: str) -> Path:
        return ensure_dir(safe_join(self.root, name))

    @property
    def configs_dir(self) -> Path: return self._dir("configs")
    @property
    def results_dir(self) -> Path: return self._dir("results")
    @property
    def artifacts_dir(self) -> Path: return self._dir("artifacts")
    @property
    def tables_dir(self) -> Path: return self._dir("tables")

    def path(self, *parts: Union[str, os.PathLike]) -> Path:
        return safe_join(self.root, *parts)

    # Configs
    def write_config(self, name: str, cfg: Json) -> Path:
        return write_json(safe_join(self.configs_dir, f"{name}.json"), cfg)

    def read_config(self, name: str) -> Json:
        return read_json(safe_join(self.configs_dir, f"{name}.json"))

    # Results
    def write_result(self, name: str, obj: Json) -> Path:
        return write_json(safe_join(self.results_dir, f"{name}.json"), obj)

    def read_result(self, name: str) -> Json:
        return read_json(safe_join(self.results_dir, f"{name}.json"))

    # Artifacts
    def write_artifact_bytes(self, relpath: str, data: bytes) -> Path:
        return atomic_write(safe_join(self.artifacts_dir, relpath), data)

    def write_artifact_text(self, relpath: str, text: str, encoding: str = "utf-8") -> Path:
        return write_text(safe_join(self.artifacts_dir, relpath), text, encoding=encoding)

    def read_artifact_bytes(self, relpath: str) -> bytes:
        return safe_join(self.artifacts_dir, relpath).read_bytes()

    # Tables
    def write_table(self, name: str, rows: Iterable[Mapping[str, Any]], *, fieldnames=None) -> Path:
        return write_table(safe_join(self.tables_dir, f"{name}.csv"), rows, fieldnames=fieldnames)

    def read_table(self, name: str) -> List[Dict[str, str]]:
        return read_table(safe_join(self.tables_dir, f"{name}.csv"))
