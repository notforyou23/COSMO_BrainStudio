"""Utilities to compute file checksums and write a manifest.

The manifest is designed for CI/CD build logs: stable ordering, relative paths,
and enough metadata to support reproducible auditing.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Iterable, Iterator, Mapping, Any, Sequence


DEFAULT_ALGORITHM = "sha256"
DEFAULT_CHUNK_SIZE = 1024 * 1024
@dataclass(frozen=True)
class ManifestEntry:
    path: str
    checksum: str
    size: int
    mtime_ns: int


def _ensure_exists(p: Path) -> Path:
    p = Path(p)
    if not p.exists():
        raise FileNotFoundError(str(p))
    return p
def iter_files(paths: Iterable[Path]) -> Iterator[Path]:
    """Yield files for a mixed set of files/directories (recursive), sorted."""
    files: list[Path] = []
    for p in paths:
        p = _ensure_exists(Path(p))
        if p.is_dir():
            for f in p.rglob("*"):
                if f.is_file():
                    files.append(f)
        elif p.is_file():
            files.append(p)
    for f in sorted(set(files), key=lambda x: x.as_posix()):
        yield f
def file_checksum(path: Path, algorithm: str = DEFAULT_ALGORITHM, chunk_size: int = DEFAULT_CHUNK_SIZE) -> str:
    """Compute a hex digest for a file."""
    h = hashlib.new(algorithm)
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def _relpath(path: Path, root: Path | None) -> str:
    p = Path(path)
    if root is None:
        return p.as_posix()
    try:
        return p.relative_to(Path(root)).as_posix()
    except Exception:
        return p.as_posix()
def build_manifest(
    *,
    inputs: Sequence[Path] = (),
    artifacts: Sequence[Path] = (),
    root: Path | None = None,
    algorithm: str = DEFAULT_ALGORITHM,
) -> dict[str, Any]:
    """Build a manifest dict with stable ordering for inputs and artifacts."""
    root_p = Path(root) if root is not None else None

    def _entries(label: str, paths: Sequence[Path]) -> list[dict[str, Any]]:
        out: list[ManifestEntry] = []
        for f in iter_files(paths):
            st = f.stat()
            out.append(
                ManifestEntry(
                    path=_relpath(f, root_p),
                    checksum=file_checksum(f, algorithm=algorithm),
                    size=int(st.st_size),
                    mtime_ns=int(st.st_mtime_ns),
                )
            )
        return [asdict(e) for e in out]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "algorithm": algorithm,
        "root": str(root_p) if root_p is not None else None,
        "inputs": _entries("inputs", list(inputs)),
        "artifacts": _entries("artifacts", list(artifacts)),
    }
def write_manifest(path: Path, manifest: Mapping[str, Any]) -> Path:
    """Write manifest JSON to disk (pretty, stable keys)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p


def manifest_checksum(manifest: Mapping[str, Any], algorithm: str = DEFAULT_ALGORITHM) -> str:
    """Checksum the canonical JSON representation of the manifest itself."""
    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    h = hashlib.new(algorithm)
    h.update(payload)
    return h.hexdigest()
