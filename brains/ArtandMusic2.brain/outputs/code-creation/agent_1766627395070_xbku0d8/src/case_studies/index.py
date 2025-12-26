"""Case studies index builder + validator.

Scans a case-studies root for per-case folders containing metadata.json and
validates metadata using schema_v1 when available (or a small fallback).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
from typing import Any, Dict, Iterable, List, Optional, Tuple


DEFAULT_METADATA_FILENAME = "metadata.json"
DEFAULT_ROOT_CANDIDATES = ("case_studies", "cases")


@dataclass(frozen=True)
class IndexItem:
    slug: str
    path: str
    metadata: Dict[str, Any]


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _fallback_validate(meta: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    if not isinstance(meta, dict):
        return ["metadata must be an object"]
    required = ("schema_version", "slug", "title", "summary", "workstream_type")
    for k in required:
        if k not in meta:
            errs.append(f"missing required field: {k}")
    if "schema_version" in meta and meta.get("schema_version") != "v1":
        errs.append("schema_version must be 'v1'")
    if "slug" in meta and (not isinstance(meta["slug"], str) or not meta["slug"].strip()):
        errs.append("slug must be a non-empty string")
    if "title" in meta and (not isinstance(meta["title"], str) or not meta["title"].strip()):
        errs.append("title must be a non-empty string")
    if "summary" in meta and (not isinstance(meta["summary"], str) or not meta["summary"].strip()):
        errs.append("summary must be a non-empty string")
    allowed = {
        "measurement_design",
        "evaluation",
        "operations",
        "strategy",
        "research",
        "product",
        "data_platform",
        "governance",
        "other",
    }
    w = meta.get("workstream_type")
    if "workstream_type" in meta and (not isinstance(w, str) or w not in allowed):
        errs.append(f"workstream_type must be one of: {sorted(allowed)}")
    return errs


def _get_validator():
    try:
        from .schema_v1 import validate_metadata as v  # type: ignore
        return v
    except Exception:
        return _fallback_validate


def find_cases_root(start: Optional[Path] = None) -> Path:
    """Find a root directory containing a case-studies folder.

    Searches upward from `start` (or CWD) for any candidate directory, else uses CWD.
    """
    start = (start or Path.cwd()).resolve()
    for p in (start, *start.parents):
        for name in DEFAULT_ROOT_CANDIDATES:
            c = p / name
            if c.is_dir():
                return c
    return start


def iter_case_dirs(root: Path) -> Iterable[Path]:
    for p in sorted(root.iterdir()):
        if p.is_dir() and not p.name.startswith(".") and p.name != "__pycache__":
            yield p


def validate_case_dir(case_dir: Path, metadata_filename: str = DEFAULT_METADATA_FILENAME) -> Tuple[Optional[IndexItem], List[str]]:
    meta_path = case_dir / metadata_filename
    if not meta_path.is_file():
        return None, [f"missing {metadata_filename}"]
    try:
        meta = _load_json(meta_path)
    except Exception as e:
        return None, [f"failed to parse {metadata_filename}: {e}"]
    validate = _get_validator()
    try:
        errs = list(validate(meta))  # schema_v1 returns list[str]
    except Exception as e:
        errs = [f"validator error: {e}"]
    if errs:
        return None, errs
    slug = str(meta.get("slug") or case_dir.name)
    item = IndexItem(slug=slug, path=str(case_dir), metadata=meta)
    return item, []


def build_index(root: Path, strict: bool = True, metadata_filename: str = DEFAULT_METADATA_FILENAME) -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []
    errors: Dict[str, List[str]] = {}
    seen: set[str] = set()
    for d in iter_case_dirs(root):
        item, errs = validate_case_dir(d, metadata_filename=metadata_filename)
        if errs:
            errors[d.name] = errs
            continue
        assert item is not None
        if item.slug in seen:
            errors[d.name] = [f"duplicate slug: {item.slug}"]
            continue
        seen.add(item.slug)
        items.append({"slug": item.slug, "path": os.path.relpath(item.path, str(root)), "metadata": item.metadata})
    index = {"root": str(root), "count": len(items), "items": items, "errors": errors}
    if strict and errors:
        msgs = []
        for k, v in errors.items():
            for e in v:
                msgs.append(f"{k}: {e}")
        raise ValueError("Index validation failed:\n" + "\n".join(msgs))
    return index


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Validate and build a case studies index by scanning folders.")
    ap.add_argument("--root", type=str, default=None, help="Case studies root folder (defaults to auto-detect).")
    ap.add_argument("--metadata", type=str, default=DEFAULT_METADATA_FILENAME, help="Metadata filename (default: metadata.json).")
    ap.add_argument("--strict", action="store_true", help="Fail (non-zero) if any cases are invalid.")
    ap.add_argument("--write", type=str, default=None, help="Write index JSON to this path.")
    ns = ap.parse_args(argv)

    root = Path(ns.root).resolve() if ns.root else find_cases_root()
    try:
        idx = build_index(root, strict=ns.strict, metadata_filename=ns.metadata)
    except Exception as e:
        print(str(e))
        return 2

    if ns.write:
        out = Path(ns.write).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(idx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        print(json.dumps({k: idx[k] for k in ("count", "errors")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
