from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib
import os
import re
from typing import Dict, Iterable, List, Mapping, Optional, Tuple, Union

_PATH_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")
_MULTI_DASH_RE = re.compile(r"[-_]{2,}")
_MAX_NAME = 120

CATEGORY_DIR = {
    "source": "source",
    "code": "source",
    "document": "docs",
    "docs": "docs",
    "data": "data",
    "image": "images",
    "audio": "audio",
    "video": "video",
    "archive": "archives",
    "log": "logs",
    "other": "misc",
}

EXT_GROUPS = {
    "source": {".py", ".js", ".ts", ".java", ".go", ".rs", ".c", ".cc", ".cpp", ".h", ".hpp", ".cs", ".rb", ".php", ".sh", ".sql", ".ipynb"},
    "docs": {".md", ".rst", ".txt", ".pdf", ".docx", ".html"},
    "data": {".json", ".csv", ".parquet", ".tsv", ".xlsx", ".yaml", ".yml", ".xml"},
    "images": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"},
    "audio": {".mp3", ".wav", ".flac", ".m4a", ".ogg"},
    "video": {".mp4", ".mov", ".mkv", ".webm"},
    "archives": {".zip", ".tar", ".gz", ".tgz", ".7z", ".rar"},
    "logs": {".log"},
}

@dataclass(frozen=True)
class CanonicalRule:
    outputs_root: Path
    category: str = "other"
    keep_ext: bool = True

def _norm_category(cat: Optional[str], suffix: str) -> str:
    if cat:
        c = cat.strip().lower()
        return CATEGORY_DIR.get(c, c) if c in CATEGORY_DIR else c
    s = suffix.lower()
    for k, exts in EXT_GROUPS.items():
        if s in exts:
            return CATEGORY_DIR.get(k, k)
    return CATEGORY_DIR["other"]

def sanitize_name(name: str) -> str:
    name = name.strip().replace(os.sep, "-")
    name = _PATH_SAFE_RE.sub("-", name)
    name = _MULTI_DASH_RE.sub("-", name).strip("._-")
    if not name:
        return "artifact"
    if len(name) > _MAX_NAME:
        name = name[:_MAX_NAME].rstrip("._-")
    return name

def file_fingerprint(path: Path, *, max_bytes: int = 10_000_000) -> str:
    h = hashlib.sha256()
    try:
        st = path.stat()
        h.update(str(st.st_size).encode("utf-8"))
        with path.open("rb") as f:
            if st.st_size <= max_bytes:
                h.update(f.read())
            else:
                head = f.read(1_000_000)
                f.seek(max(st.st_size - 1_000_000, 0))
                tail = f.read(1_000_000)
                h.update(head)
                h.update(tail)
    except FileNotFoundError:
        h.update(str(path.as_posix()).encode("utf-8"))
    return h.hexdigest()

def _path_fingerprint(path: Path) -> str:
    return hashlib.sha256(path.as_posix().encode("utf-8")).hexdigest()

def canonical_destination(old_path: Union[str, Path], rule: CanonicalRule) -> Path:
    p = Path(old_path)
    suffix = p.suffix.lower()
    cat_dir = _norm_category(rule.category, suffix)
    base = sanitize_name(p.stem)
    ext = suffix if rule.keep_ext else ""
    fp = file_fingerprint(p) if p.exists() else _path_fingerprint(p)
    leaf = f"{base}{ext}"
    return rule.outputs_root / cat_dir / leaf

def resolve_collision(dest: Path, old_path: Union[str, Path]) -> Path:
    if not dest.exists():
        return dest
    p = Path(old_path)
    try:
        same = dest.is_file() and p.is_file() and file_fingerprint(dest) == file_fingerprint(p)
        if same:
            return dest
    except Exception:
        pass
    base = sanitize_name(dest.stem)
    ext = dest.suffix
    tag = (file_fingerprint(p) if p.exists() else _path_fingerprint(p))[:8]
    return dest.with_name(f"{base}-{tag}{ext}")

def compute_mapping(old_path: Union[str, Path], outputs_root: Union[str, Path], category: Optional[str] = None) -> Tuple[Path, Path]:
    op = Path(old_path)
    root = Path(outputs_root)
    rule = CanonicalRule(outputs_root=root, category=category or "other")
    dest = canonical_destination(op, rule)
    dest = resolve_collision(dest, op)
    return op, dest

def compute_mappings(records: Iterable[Mapping[str, object]], outputs_root: Union[str, Path]) -> Dict[str, str]:
    root = Path(outputs_root)
    out: Dict[str, str] = {}
    for r in records:
        p = Path(str(r.get("path")))
        cat = r.get("category")
        cat_s = str(cat) if cat is not None else None
        _, dest = compute_mapping(p, root, cat_s)
        out[str(p)] = str(dest)
    return out

def ensure_under_root(path: Union[str, Path], root: Union[str, Path]) -> Path:
    p = Path(path)
    r = Path(root)
    try:
        rp = p.resolve()
        rr = r.resolve()
        if rr in rp.parents or rp == rr:
            return rp
    except Exception:
        pass
    raise ValueError(f"Path not under root: {p} (root={r})")
