"""Export utilities for deterministic artifact emission.

This module writes refactored artifacts into stable on-disk layouts with
predictable filenames and normalized file contents.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union
import hashlib
import json
import os
import re


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    """Return a stable filesystem-friendly slug (lowercase, ascii-ish)."""
    v = (value or "").strip().lower()
    v = v.encode("utf-8", "ignore").decode("utf-8")
    v = _SLUG_RE.sub("-", v).strip("-")
    return v or "artifact"


def normalize_text(text: str) -> str:
    """Normalize newlines and ensure a trailing newline for text files."""
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    return t if t.endswith("\n") else t + "\n"


def dumps_json(obj: Any) -> str:
    """Deterministic JSON serialization (sorted keys, LF newline)."""
    return normalize_text(
        json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2)  # type: ignore[arg-type]
    )


def _sha8(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]


@dataclass(frozen=True)
class ExportedFile:
    """A normalized file ready to be written."""

    relpath: str
    content: str
    mode: str = "text"  # "text" or "json"


def resolve_relpath(
    artifact: Mapping[str, Any],
    *,
    layout: str = "by_kind",
    default_suffix: str = ".txt",
) -> str:
    """Compute a stable relative path for an artifact mapping.

    Supported keys: relpath, kind, name, suffix, text/content, id.
    """
    if artifact.get("relpath"):
        return str(artifact["relpath"]).replace("\\", "/").lstrip("/")
    kind = slugify(str(artifact.get("kind") or "artifact"))
    name = slugify(str(artifact.get("name") or artifact.get("id") or kind))
    suffix = str(artifact.get("suffix") or default_suffix)
    if not suffix.startswith("."):
        suffix = "." + suffix
    subdir = kind if layout == "by_kind" else ""
    filename = f"{name}{suffix}"
    if layout == "flat":
        return filename
    if layout == "by_kind":
        return f"{subdir}/{filename}"
    raise ValueError(f"Unknown layout: {layout!r}")


def plan_exports(
    artifacts: Iterable[Mapping[str, Any]],
    *,
    layout: str = "by_kind",
) -> Tuple[List[ExportedFile], Dict[str, Any]]:
    """Convert artifacts into ExportedFile entries plus a manifest dict."""
    files: List[ExportedFile] = []
    manifest_items: List[Dict[str, Any]] = []
    for a in artifacts:
        text = a.get("text")
        if text is None:
            text = a.get("content", "")
        mode = str(a.get("mode") or ("json" if a.get("is_json") else "text"))
        relpath = resolve_relpath(a, layout=layout, default_suffix=str(a.get("suffix") or ".txt"))
        if mode == "json" and not isinstance(text, str):
            content = dumps_json(text)
        elif mode == "json":
            content = dumps_json(json.loads(text)) if text.strip().startswith(("{", "[")) else dumps_json(text)
        else:
            content = normalize_text(str(text))
        files.append(ExportedFile(relpath=relpath, content=content, mode=mode))
        manifest_items.append(
            {
                "relpath": relpath,
                "kind": a.get("kind"),
                "name": a.get("name"),
                "sha256_8": _sha8(content),
                "bytes": len(content.encode("utf-8")),
            }
        )
    manifest = {"version": 1, "layout": layout, "files": sorted(manifest_items, key=lambda x: x["relpath"])}
    return sorted(files, key=lambda f: f.relpath), manifest


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(content, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def export(
    artifacts: Iterable[Mapping[str, Any]],
    out_dir: Union[str, Path],
    *,
    layout: str = "by_kind",
    write_manifest: bool = True,
    manifest_name: str = "manifest.json",
) -> List[Path]:
    """Write artifacts to disk deterministically and return written paths."""
    out = Path(out_dir)
    files, manifest = plan_exports(artifacts, layout=layout)
    written: List[Path] = []
    for f in files:
        p = out / f.relpath
        _atomic_write_text(p, f.content)
        written.append(p)
    if write_manifest:
        mp = out / manifest_name
        _atomic_write_text(mp, dumps_json(manifest))
        written.append(mp)
    return sorted(written)
