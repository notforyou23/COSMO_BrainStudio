"""Core data models and loaders for representing, reading, and normalizing artifact files.

This module is dependency-free: it provides a stable schema for artifact inputs and
helpers to infer metadata from common export filename conventions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence
import hashlib
import re
_KIND_BY_SUFFIX = {
    ".py": "python",
    ".md": "markdown",
    ".toml": "toml",
    ".json": "json",
    ".txt": "text",
}

_EXPORT_NAME_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}T[^_]+)_(?P<label>.+?)_stage(?P<stage>\d+)"
    r"(?:_attempt(?P<attempt>\d+))?_(?P<role>prompt|export)(?:_.+)?\.(?P<ext>[^.]+)$"
)
@dataclass(frozen=True)
class Artifact:
    """Normalized representation of a single artifact file."""
    path: Path
    relpath: str
    kind: str
    text: str
    sha256: str
    size: int
    mtime: float
    meta: Mapping[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.path.name
def infer_kind(path: Path) -> str:
    """Infer an artifact kind from filename/suffix."""
    name = path.name.lower()
    if name == "readme.md":
        return "readme"
    if name == "pyproject.toml":
        return "pyproject"
    return _KIND_BY_SUFFIX.get(path.suffix.lower(), "unknown")
def parse_export_filename(name: str) -> Dict[str, Any]:
    """Parse common export filenames into metadata.

    Examples:
      - 2025-12-24T01-49-28-186Z_README_md_stage1_attempt1_prompt.txt
      - 2025-12-24T01-49-28-186Z_pyproject_toml_stage1_export_export_prompt.txt
    """
    m = _EXPORT_NAME_RE.match(name)
    if not m:
        return {}
    d: Dict[str, Any] = m.groupdict()
    for k in ("stage", "attempt"):
        if d.get(k) is not None:
            d[k] = int(d[k])
        else:
            d.pop(k, None)
    label = d.get("label") or ""
    if label and "_" in label:
        parts = label.split("_")
        # Heuristic: convert FOO_bar -> FOO.bar when last part looks like an extension.
        if len(parts) >= 2 and parts[-1].isalpha() and 1 <= len(parts[-1]) <= 5:
            d["label_normalized"] = ".".join(parts)
    return d
def load_artifact(
    path: Path,
    *,
    root: Optional[Path] = None,
    encoding: str = "utf-8",
    errors: str = "replace",
    max_bytes: Optional[int] = None,
) -> Artifact:
    """Read and normalize an artifact file."""
    p = Path(path)
    b = p.read_bytes()
    if max_bytes is not None:
        b = b[:max_bytes]
    text = b.decode(encoding, errors=errors)
    stat = p.stat()
    sha = hashlib.sha256(b).hexdigest()
    rel = str(p.relative_to(root)) if root else str(p)
    meta: Dict[str, Any] = {}
    meta.update(parse_export_filename(p.name))
    return Artifact(
        path=p,
        relpath=rel,
        kind=infer_kind(p),
        text=text,
        sha256=sha,
        size=stat.st_size,
        mtime=stat.st_mtime,
        meta=meta,
    )
def load_artifacts(
    paths: Sequence[Path],
    *,
    root: Optional[Path] = None,
    **kwargs: Any,
) -> List[Artifact]:
    """Load multiple artifacts deterministically (sorted by relpath)."""
    arts = [load_artifact(p, root=root, **kwargs) for p in paths]
    return sorted(arts, key=lambda a: a.relpath)
