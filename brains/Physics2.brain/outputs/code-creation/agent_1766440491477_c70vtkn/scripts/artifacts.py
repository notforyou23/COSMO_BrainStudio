"""Artifact utilities: redact secrets, build deterministic manifests, and package logs/results.

Designed for CI: create a staging tree with redaction applied, emit a stable manifest,
and package into .tar.gz or .zip with normalized metadata for reproducible uploads.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import fnmatch
import hashlib
import json
import os
import re
import shutil
import stat
import tarfile
import zipfile
from typing import Iterable, Iterator, List, Optional, Sequence, Tuple
# Regexes tuned to catch common CI secrets without being overly expensive.
_SECRET_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"(?i)\bghp_[A-Za-z0-9]{20,}\b"), "REDACTED_GH_TOKEN"),
    (re.compile(r"(?i)\bgithub_pat_[A-Za-z0-9_]{20,}\b"), "REDACTED_GH_PAT"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "REDACTED_AWS_ACCESS_KEY_ID"),
    (re.compile(r"(?is)-----BEGIN (?:RSA )?PRIVATE KEY-----.*?-----END (?:RSA )?PRIVATE KEY-----"),
     "REDACTED_PRIVATE_KEY_BLOCK"),
    (re.compile(r"(?im)^(\s*(?:\w+_)?(?:token|secret|password|passwd|api[_-]?key)\s*=\s*).+$"),
     r"\1REDACTED"),
]
_TEXT_EXTS = {".log", ".txt", ".json", ".yml", ".yaml", ".env", ".ini", ".cfg", ".md"}
def redact_text(text: str) -> str:
    for rx, repl in _SECRET_PATTERNS:
        text = rx.sub(repl, text)
    return text


def redact_bytes(data: bytes) -> bytes:
    try:
        s = data.decode("utf-8")
    except UnicodeDecodeError:
        s = data.decode("utf-8", errors="ignore")
    return redact_text(s).encode("utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
def _rel_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def iter_files(
    root: Path,
    includes: Sequence[str] = ("**/*",),
    excludes: Sequence[str] = (),
) -> Iterator[Path]:
    root = root.resolve()
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = _rel_posix(p, root)
        if includes and not any(fnmatch.fnmatch(rel, pat) for pat in includes):
            continue
        if excludes and any(fnmatch.fnmatch(rel, pat) for pat in excludes):
            continue
        yield p
@dataclass(frozen=True)
class ManifestEntry:
    path: str
    size: int
    sha256: str


def build_manifest(root: Path, files: Iterable[Path]) -> List[ManifestEntry]:
    root = root.resolve()
    entries: List[ManifestEntry] = []
    for p in files:
        entries.append(ManifestEntry(_rel_posix(p, root), p.stat().st_size, sha256_file(p)))
    entries.sort(key=lambda e: e.path)
    return entries


def write_manifest(path: Path, entries: Sequence[ManifestEntry]) -> None:
    payload = {
        "version": 1,
        "entries": [e.__dict__ for e in entries],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
def stage_tree(
    src_root: Path,
    dst_root: Path,
    includes: Sequence[str] = ("**/*",),
    excludes: Sequence[str] = (),
) -> List[Path]:
    """Copy src_root -> dst_root applying redaction to likely-text files.

    Returns a list of staged file paths (in dst_root), deterministically ordered.
    """
    src_root = src_root.resolve()
    dst_root = dst_root.resolve()
    if dst_root.exists():
        shutil.rmtree(dst_root)
    dst_root.mkdir(parents=True, exist_ok=True)

    staged: List[Path] = []
    for src in iter_files(src_root, includes=includes, excludes=excludes):
        rel = src.relative_to(src_root)
        dst = dst_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix.lower() in _TEXT_EXTS:
            dst.write_bytes(redact_bytes(src.read_bytes()))
        else:
            shutil.copy2(src, dst)
        os.utime(dst, (0, 0))  # normalize mtimes for reproducible archives
        staged.append(dst)
    staged.sort(key=lambda p: p.relative_to(dst_root).as_posix())
    return staged
def create_tar_gz(staged_root: Path, out_path: Path) -> Path:
    staged_root = staged_root.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    def _filter(ti: tarfile.TarInfo) -> tarfile.TarInfo:
        ti.uid = ti.gid = 0
        ti.uname = ti.gname = ""
        ti.mtime = 0
        if ti.mode:
            ti.mode = 0o644 if ti.isfile() else 0o755
        return ti

    with tarfile.open(out_path, "w:gz") as tf:
        tf.add(staged_root, arcname=".", filter=_filter)
    return out_path


def create_zip(staged_root: Path, out_path: Path) -> Path:
    staged_root = staged_root.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    epoch = (1980, 1, 1, 0, 0, 0)

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in iter_files(staged_root):
            rel = _rel_posix(p, staged_root)
            zi = zipfile.ZipInfo(rel, date_time=epoch)
            mode = 0o644
            zi.external_attr = (mode & 0xFFFF) << 16
            zf.writestr(zi, p.read_bytes())
    return out_path
def prepare_artifacts(
    src_root: Path,
    work_dir: Path,
    *,
    includes: Sequence[str] = ("**/*",),
    excludes: Sequence[str] = ("**/__pycache__/**", "**/*.pyc"),
    archive_name: str = "artifacts",
    fmt: str = "tar.gz",
) -> Tuple[Path, Path]:
    """Stage+manifest+archive. Returns (archive_path, manifest_path)."""
    work_dir = work_dir.resolve()
    staged_root = work_dir / "staged"
    staged_files = stage_tree(src_root, staged_root, includes=includes, excludes=excludes)
    manifest_entries = build_manifest(staged_root, staged_files)
    manifest_path = work_dir / "manifest.json"
    write_manifest(manifest_path, manifest_entries)
    # Include manifest inside the staged tree for easier debugging.
    shutil.copy2(manifest_path, staged_root / "manifest.json")
    os.utime(staged_root / "manifest.json", (0, 0))

    if fmt == "zip":
        archive_path = work_dir / f"{archive_name}.zip"
        return create_zip(staged_root, archive_path), manifest_path
    archive_path = work_dir / f"{archive_name}.tar.gz"
    return create_tar_gz(staged_root, archive_path), manifest_path
