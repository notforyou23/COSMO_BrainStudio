"""Case study index helpers.

This module provides safe, deterministic read/update/sort/write utilities for a
case-study index.json file used to discover case studies under outputs/.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple, Union
import json
import os
import tempfile
from datetime import datetime, timezone
JsonValue = Any
JsonObj = Dict[str, JsonValue]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> JsonValue:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json_atomic(path: Path, obj: JsonValue) -> None:
    _ensure_parent(path)
    data = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    tmp_dir = str(path.parent)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=tmp_dir, text=True)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(str(tmp_path), str(path))
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
def normalize_entry(entry: Mapping[str, JsonValue]) -> JsonObj:
    """Normalize a case study index entry.

    Required: slug (str)
    Recommended: title (str), path (str), updated_at (str)
    Preserves additional keys but enforces deterministic types for common fields.
    """
    if not isinstance(entry, Mapping):
        raise TypeError("entry must be a mapping")
    slug = entry.get("slug")
    if not isinstance(slug, str) or not slug.strip():
        raise ValueError("entry.slug must be a non-empty string")
    out: JsonObj = dict(entry)  # preserve extras
    out["slug"] = slug.strip()

    title = out.get("title")
    if title is not None and not isinstance(title, str):
        out["title"] = str(title)

    path = out.get("path")
    if path is not None and not isinstance(path, str):
        out["path"] = str(path)

    tags = out.get("tags")
    if tags is None:
        pass
    elif isinstance(tags, (list, tuple)):
        out["tags"] = [str(t) for t in tags]
    else:
        out["tags"] = [str(tags)]

    updated_at = out.get("updated_at")
    if updated_at is not None and not isinstance(updated_at, str):
        out["updated_at"] = str(updated_at)

    return out


def _entry_sort_key(entry: Mapping[str, JsonValue]) -> Tuple[str, str]:
    slug = str(entry.get("slug", "")).lower()
    title = str(entry.get("title", "")).lower()
    return (slug, title)


def normalize_index(index: Optional[Mapping[str, JsonValue]]) -> JsonObj:
    """Ensure the index has a stable top-level structure."""
    if index is None:
        return {"case_studies": [], "updated_at": _utc_now_iso(), "version": 1}
    if not isinstance(index, Mapping):
        raise TypeError("index must be a mapping")
    out: JsonObj = dict(index)
    entries = out.get("case_studies")
    if entries is None:
        entries_list: List[JsonObj] = []
    elif isinstance(entries, list):
        entries_list = [normalize_entry(e) for e in entries]  # type: ignore[arg-type]
    else:
        raise TypeError("index.case_studies must be a list")
    out["case_studies"] = entries_list
    if "version" not in out:
        out["version"] = 1
    if "updated_at" not in out or not isinstance(out.get("updated_at"), str):
        out["updated_at"] = _utc_now_iso()
    return out
def read_index(index_path: Union[str, Path]) -> JsonObj:
    """Read index.json; returns a normalized structure (creates in-memory default if missing)."""
    path = Path(index_path)
    if not path.exists():
        return normalize_index(None)
    return normalize_index(_read_json(path))  # type: ignore[arg-type]


def sort_index(index: MutableMapping[str, JsonValue]) -> JsonObj:
    """Deterministically sort entries and de-duplicate by slug (last write wins)."""
    norm = normalize_index(index)
    entries: List[JsonObj] = list(norm["case_studies"])  # type: ignore[assignment]
    by_slug: Dict[str, JsonObj] = {}
    for e in entries:
        by_slug[str(e["slug"])] = e
    sorted_entries = sorted(by_slug.values(), key=_entry_sort_key)
    norm["case_studies"] = sorted_entries
    return norm


def upsert_entry(index: MutableMapping[str, JsonValue], entry: Mapping[str, JsonValue]) -> JsonObj:
    """Insert or replace an entry by slug, then sort."""
    norm = normalize_index(index)
    e = normalize_entry(entry)
    entries: List[JsonObj] = list(norm["case_studies"])  # type: ignore[assignment]
    replaced = False
    for i, existing in enumerate(entries):
        if str(existing.get("slug")) == e["slug"]:
            entries[i] = e
            replaced = True
            break
    if not replaced:
        entries.append(e)
    norm["case_studies"] = entries
    norm["updated_at"] = _utc_now_iso()
    return sort_index(norm)


def remove_entry(index: MutableMapping[str, JsonValue], slug: str) -> JsonObj:
    """Remove an entry by slug (no-op if missing), then sort."""
    if not isinstance(slug, str) or not slug.strip():
        raise ValueError("slug must be a non-empty string")
    s = slug.strip()
    norm = normalize_index(index)
    entries: List[JsonObj] = list(norm["case_studies"])  # type: ignore[assignment]
    norm["case_studies"] = [e for e in entries if str(e.get("slug")) != s]
    norm["updated_at"] = _utc_now_iso()
    return sort_index(norm)


def write_index(index_path: Union[str, Path], index: Mapping[str, JsonValue]) -> JsonObj:
    """Normalize, sort, and atomically write the index.json file."""
    path = Path(index_path)
    norm = sort_index(dict(index))
    _write_json_atomic(path, norm)
    return norm
