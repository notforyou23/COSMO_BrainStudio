"""
Safe migration/copy helpers for canonicalizing scattered outputs into a single
canonical outputs/ tree.

Design goals:
- deterministic destination naming
- collision-safe copies (no silent overwrite)
- optional pruning of superseded canonical files
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence
import hashlib
import os
import shutil


@dataclass(frozen=True)
class CopyResult:
    src: Path
    dst: Path
    action: str  # "copied" | "skipped_identical" | "skipped_missing"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _is_same_file(a: Path, b: Path) -> bool:
    try:
        if a.stat().st_size != b.stat().st_size:
            return False
    except FileNotFoundError:
        return False
    # Quick path: same inode on same filesystem
    try:
        return os.path.samefile(a, b)
    except Exception:
        pass
    return _sha256(a) == _sha256(b)


def _next_available(dst: Path) -> Path:
    if not dst.exists():
        return dst
    stem, suf = dst.stem, dst.suffix
    parent = dst.parent
    for i in range(1, 10_000):
        cand = parent / f"{stem}__v{i}{suf}"
        if not cand.exists():
            return cand
    raise RuntimeError(f"Too many collisions for destination: {dst}")


def safe_copy_file(
    src: Path,
    dst: Path,
    *,
    collision: str = "version",  # "version" | "skip_if_identical" | "error"
    preserve_metadata: bool = True,
) -> CopyResult:
    src = Path(src)
    dst = Path(dst)
    if not src.exists():
        return CopyResult(src=src, dst=dst, action="skipped_missing")
    if src.is_dir():
        raise IsADirectoryError(f"safe_copy_file expected a file, got dir: {src}")

    ensure_dir(dst.parent)

    if dst.exists():
        if collision == "skip_if_identical" and _is_same_file(src, dst):
            return CopyResult(src=src, dst=dst, action="skipped_identical")
        if collision == "error":
            raise FileExistsError(f"Destination exists: {dst}")
        if collision == "version":
            dst = _next_available(dst)
        else:
            raise ValueError(f"Unknown collision policy: {collision}")

    if preserve_metadata:
        shutil.copy2(src, dst)
    else:
        shutil.copyfile(src, dst)
    return CopyResult(src=src, dst=dst, action="copied")


def safe_copy_any(
    src: Path,
    dst: Path,
    *,
    collision: str = "version",
    preserve_metadata: bool = True,
) -> Sequence[CopyResult]:
    src = Path(src)
    dst = Path(dst)
    if not src.exists():
        return (CopyResult(src=src, dst=dst, action="skipped_missing"),)

    if src.is_file():
        return (safe_copy_file(src, dst, collision=collision, preserve_metadata=preserve_metadata),)

    # Directory copy: copy files recursively; destination dir may exist.
    results: list[CopyResult] = []
    ensure_dir(dst)
    for p in sorted(src.rglob("*")):
        if p.is_dir():
            continue
        rel = p.relative_to(src)
        results.extend(
            safe_copy_any(
                p,
                dst / rel,
                collision=collision,
                preserve_metadata=preserve_metadata,
            )
        )
    return tuple(results)


def migrate_selected(
    selections: Iterable[tuple[Path, Path]],
    *,
    outputs_root: Path,
    collision: str = "version",
    preserve_metadata: bool = True,
) -> list[CopyResult]:
    """
    selections: iterable of (src_path, canonical_relpath_under_outputs)
    outputs_root: path to canonical outputs directory (created if missing)
    """
    outputs_root = ensure_dir(Path(outputs_root))
    results: list[CopyResult] = []
    for src, rel in selections:
        srcp = Path(src)
        relp = Path(rel)
        if relp.is_absolute():
            raise ValueError(f"canonical relpath must be relative: {relp}")
        dst = outputs_root / relp
        results.extend(
            safe_copy_any(srcp, dst, collision=collision, preserve_metadata=preserve_metadata)
        )
    return results


def prune_canonical(
    outputs_root: Path,
    keep_relpaths: Iterable[Path],
    *,
    dry_run: bool = False,
    restrict_to: Optional[Path] = None,
) -> list[Path]:
    """
    Deletes files under outputs_root not in keep_relpaths (normalized relative paths).
    If restrict_to is provided, only files under that relative subdir are considered.
    Returns list of removed paths (absolute).
    """
    outputs_root = Path(outputs_root)
    keep = {Path(p).as_posix().lstrip("/") for p in keep_relpaths}
    removed: list[Path] = []
    if not outputs_root.exists():
        return removed

    root = outputs_root / restrict_to if restrict_to else outputs_root
    root = root.resolve()
    if outputs_root.resolve() not in root.parents and outputs_root.resolve() != root:
        raise ValueError("restrict_to must be within outputs_root")

    for p in sorted(root.rglob("*")):
        if p.is_dir():
            continue
        try:
            rel = p.resolve().relative_to(outputs_root.resolve()).as_posix()
        except Exception:
            continue
        if rel not in keep:
            if not dry_run:
                try:
                    p.unlink()
                except FileNotFoundError:
                    pass
            removed.append(p)

    # Cleanup empty directories (best-effort)
    if not dry_run:
        for d in sorted([q for q in root.rglob("*") if q.is_dir()], reverse=True):
            try:
                next(d.iterdir())
            except StopIteration:
                try:
                    d.rmdir()
                except OSError:
                    pass
    return removed
