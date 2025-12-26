from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import builtins
import contextlib
import datetime as _dt
import hashlib
import json
import os
import secrets
from typing import Any, Dict, Iterable, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
QA_ROOT = (PROJECT_ROOT / "outputs" / "qa").resolve()
def canonical_path(p: os.PathLike | str) -> Path:
    return Path(p).expanduser().resolve()

def ensure_within(root: Path, p: Path) -> Path:
    root_r = canonical_path(root)
    p_r = canonical_path(p)
    try:
        p_r.relative_to(root_r)
    except Exception as e:
        raise ValueError(f"Path escapes root: {p_r} not within {root_r}") from e
    return p_r

def new_run_id(prefix: str = "") -> str:
    ts = _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%S.%f")[:-3] + "Z"
    suf = secrets.token_hex(2)
    return f"{prefix}{ts}_{suf}" if prefix else f"{ts}_{suf}
@contextlib.contextmanager
def enforce_writes_under(root: Path = QA_ROOT):
    root_r = canonical_path(root)
    _open = builtins.open
    _os_open = os.open

    def _is_write_mode(mode: str) -> bool:
        return any(ch in mode for ch in ("w", "a", "x", "+"))

    def _guard_path(pathlike: Any):
        if isinstance(pathlike, (str, os.PathLike)):
            ensure_within(root_r, Path(pathlike))
        return pathlike

    def guarded_open(file, mode="r", *args, **kwargs):
        if _is_write_mode(mode):
            _guard_path(file)
        return _open(file, mode, *args, **kwargs)

    def guarded_os_open(path, flags, *args, **kwargs):
        write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
        if flags & write_flags:
            _guard_path(path)
        return _os_open(path, flags, *args, **kwargs)

    builtins.open = guarded_open
    os.open = guarded_os_open
    try:
        yield root_r
    finally:
        builtins.open = _open
        os.open = _os_open
def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def iter_files(root: Path) -> Iterable[Path]:
    root = canonical_path(root)
    for p in sorted(root.rglob("*")):
        if p.is_file():
            yield p
@dataclass(frozen=True)
class QARun:
    run_id: str
    run_dir: Path
    qa_root: Path = QA_ROOT

    def path(self, *parts: str) -> Path:
        p = (self.run_dir.joinpath(*parts))
        return ensure_within(self.run_dir, p)

    def write_text(self, rel: str, text: str, encoding: str = "utf-8") -> Path:
        p = self.path(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding=encoding)
        return p

    def write_json(self, rel: str, obj: Any, indent: int = 2) -> Path:
        p = self.path(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj, indent=indent, ensure_ascii=False) + "\n", encoding="utf-8")
        return p

    def finalize_indexes(self) -> Tuple[Path, Path]:
        files: List[Dict[str, Any]] = []
        for p in iter_files(self.run_dir):
            rel = str(p.relative_to(self.run_dir)).replace(os.sep, "/")
            if rel in ("index.json", "manifest.json"):
                continue
            files.append({"path": rel, "bytes": p.stat().st_size, "sha256": sha256_file(p)})
        index = {"run_id": self.run_id, "root": str(self.run_dir), "files": files}
        manifest = {
            "schema": "qa.manifest.v1",
            "run_id": self.run_id,
            "created_utc": _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "file_count": len(files),
            "files": [f["path"] for f in files],
        }
        idx_p = self.write_json("index.json", index)
        man_p = self.write_json("manifest.json", manifest)
        return idx_p, man_p
def init_qa_run(run_id: Optional[str] = None, qa_root: Path = QA_ROOT, prefix: str = "") -> QARun:
    qa_root_r = canonical_path(qa_root)
    qa_root_r.mkdir(parents=True, exist_ok=True)
    rid = run_id or new_run_id(prefix=prefix)
    run_dir = ensure_within(qa_root_r, qa_root_r / rid)
    run_dir.mkdir(parents=True, exist_ok=False)
    return QARun(run_id=rid, run_dir=run_dir, qa_root=qa_root_r)
