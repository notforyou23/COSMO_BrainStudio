"""refactor_modularize.export

Small export helpers used by the refactoring pipeline.

Responsibilities:
- Serialize artifacts (text / JSON) to disk.
- Enforce stable naming conventions and simple versioning.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Optional, Union
import json
import re
__all__ = [
    "ExportResult",
    "default_run_id",
    "slugify",
    "versioned_path",
    "write_text",
    "write_json",
    "export_artifact",
    "export_artifacts",
]
_SLUG_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def slugify(value: str, *, max_len: int = 80) -> str:
    """Convert arbitrary text to a filesystem-friendly token."""
    value = value.strip().replace(" ", "_")
    value = _SLUG_RE.sub("-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-._")
    return (value[:max_len] or "artifact")
def default_run_id(dt: Optional[datetime] = None) -> str:
    """Return a sortable run id like 2025-12-24T01-56-08-639Z."""
    dt = dt or datetime.now(timezone.utc)
    ms = int(dt.microsecond / 1000)
    return dt.strftime("%Y-%m-%dT%H-%M-%S-") + f"{ms:03d}Z"
def versioned_path(path: Path, *, overwrite: bool = False) -> Path:
    """If path exists and overwrite=False, append _vN before suffix."""
    if overwrite or not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    i = 2
    while True:
        candidate = path.with_name(f"{stem}_v{i}{suffix}")
        if not candidate.exists():
            return candidate
        i += 1
def _atomic_write(path: Path, data: Union[str, bytes], *, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    if isinstance(data, str):
        tmp.write_text(data, encoding=encoding)
    else:
        tmp.write_bytes(data)
    tmp.replace(path)
def write_text(path: Path, text: str, *, encoding: str = "utf-8", overwrite: bool = False) -> Path:
    """Write text to a (possibly versioned) path and return the final path."""
    path = versioned_path(path, overwrite=overwrite)
    _atomic_write(path, text, encoding=encoding)
    return path


def write_json(
    path: Path,
    obj: Any,
    *,
    encoding: str = "utf-8",
    indent: int = 2,
    sort_keys: bool = True,
    overwrite: bool = False,
) -> Path:
    """Write JSON to a (possibly versioned) path and return the final path."""
    text = json.dumps(obj, ensure_ascii=False, indent=indent, sort_keys=sort_keys) + "\n"
    return write_text(path, text, encoding=encoding, overwrite=overwrite)
@dataclass(frozen=True)
class ExportResult:
    """Metadata about a single exported artifact."""
    name: str
    path: Path
    format: str  # "text" | "json"
def export_artifact(
    *,
    root: Union[str, Path],
    project: str,
    name: str,
    value: Any,
    run_id: Optional[str] = None,
    ext: Optional[str] = None,
    overwrite: bool = False,
) -> ExportResult:
    """Export one artifact to disk using naming + versioning conventions.

    Naming: {run_id}_{project}_{name}.{ext}
    - ext defaults to "md" for strings and "json" otherwise.
    """
    root_p = Path(root)
    run_id = run_id or default_run_id()
    project_s = slugify(project)
    name_s = slugify(name)
    if ext is None:
        fmt = "text" if isinstance(value, str) else "json"
        ext = "md" if fmt == "text" else "json"
    ext = ext.lstrip(".")
    path = root_p / f"{run_id}_{project_s}_{name_s}.{ext}"
    if isinstance(value, str) and ext.lower() != "json":
        out_path = write_text(path, value, overwrite=overwrite)
        return ExportResult(name=name, path=out_path, format="text")
    out_path = write_json(path, value, overwrite=overwrite)
    return ExportResult(name=name, path=out_path, format="json")
def export_artifacts(
    artifacts: Mapping[str, Any],
    *,
    root: Union[str, Path],
    project: str,
    run_id: Optional[str] = None,
    overwrite: bool = False,
    manifest_name: str = "manifest",
) -> MutableMapping[str, ExportResult]:
    """Export a mapping of artifact_name -> value. Also writes a manifest JSON."""
    run_id = run_id or default_run_id()
    results: MutableMapping[str, ExportResult] = {}
    for name, value in artifacts.items():
        results[name] = export_artifact(
            root=root, project=project, name=name, value=value, run_id=run_id, overwrite=overwrite
        )
    manifest = {
        "run_id": run_id,
        "project": project,
        "artifacts": {k: str(v.path) for k, v in results.items()},
    }
    export_artifact(
        root=root,
        project=project,
        name=manifest_name,
        value=manifest,
        run_id=run_id,
        ext="json",
        overwrite=overwrite,
    )
    return results
