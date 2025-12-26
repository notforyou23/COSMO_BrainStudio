from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Callable, Dict, List, Tuple
import hashlib, json, os, re, shutil
from datetime import datetime, timezone
@dataclass(frozen=True)
class Artifact:
    path: Path
    rel_key: str
    size: int
    mtime: float

    @property
    def ext(self) -> str:
        return self.path.suffix.lower()

    def score(self, ext_priority: Dict[str, int]) -> Tuple[int, int, float]:
        return (ext_priority.get(self.ext, 0), self.size, self.mtime)
def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(chunk_size), b""):
            h.update(b)
    return h.hexdigest()
def _iter_files(root: Path, exclude_dirs: Iterable[str], max_depth: Optional[int]) -> Iterable[Path]:
    root = root.resolve()
    ex = set(exclude_dirs)
    root_parts = len(root.parts)
    for dirpath, dirnames, filenames in os.walk(root):
        dp = Path(dirpath)
        depth = len(dp.parts) - root_parts
        if max_depth is not None and depth > max_depth:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d not in ex and not d.startswith(".")]
        for fn in filenames:
            if fn.startswith("."):
                continue
            p = dp / fn
            if p.is_file():
                yield p
def discover_artifacts(
    roots: Iterable[Path],
    *,
    rel_key: Optional[Callable[[Path, Path], str]] = None,
    include: Optional[re.Pattern] = None,
    exclude: Optional[re.Pattern] = None,
    exclude_dirs: Iterable[str] = ("__pycache__", ".git", ".pytest_cache", "node_modules"),
    max_depth: Optional[int] = None,
) -> List[Artifact]:
    out: List[Artifact] = []
    for r in roots:
        r = Path(r)
        if not r.exists():
            continue
        for p in _iter_files(r, exclude_dirs, max_depth):
            s = str(p)
            if include and not include.search(s):
                continue
            if exclude and exclude.search(s):
                continue
            st = p.stat()
            key = rel_key(p, r) if rel_key else str(p.relative_to(r))
            out.append(Artifact(path=p, rel_key=key.replace("\\", "/"), size=int(st.st_size), mtime=float(st.st_mtime)))
    return out
def select_best_by_key(
    artifacts: Iterable[Artifact],
    *,
    ext_priority: Optional[Dict[str, int]] = None,
) -> Dict[str, Artifact]:
    ext_priority = ext_priority or {
        ".html": 70, ".pdf": 65, ".png": 60, ".jpg": 58, ".jpeg": 58, ".svg": 57,
        ".json": 55, ".md": 50, ".txt": 45, ".csv": 45, ".tsv": 44,
        ".zip": 40, ".tar": 40, ".gz": 38, ".parquet": 38,
        ".pkl": 25, ".pickle": 25, ".bin": 20, ".log": 5,
    }
    best: Dict[str, Artifact] = {}
    for a in artifacts:
        k = a.rel_key
        cur = best.get(k)
        if cur is None or a.score(ext_priority) > cur.score(ext_priority):
            best[k] = a
    return best
def _safe_dest_name(name: str) -> str:
    name = name.replace("\\", "/").lstrip("/")
    name = re.sub(r"[^A-Za-z0-9._/\-]+", "_", name)
    name = re.sub(r"/{2,}", "/", name)
    return name
def copy_artifacts(
    selected: Dict[str, Artifact],
    dest_dir: Path,
    *,
    flatten: bool = False,
    on_collision: str = "hash",
) -> List[Path]:
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []
    for key, art in sorted(selected.items(), key=lambda kv: kv[0]):
        rel = Path(_safe_dest_name(Path(key).name if flatten else key))
        dst = dest_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            if on_collision == "skip":
                continue
            if on_collision == "overwrite":
                pass
            elif on_collision == "hash":
                stem, suf = dst.stem, dst.suffix
                tag = sha256_file(art.path)[:12]
                dst = dst.with_name(f"{stem}.{tag}{suf}")
            else:
                raise ValueError(f"Unknown on_collision: {on_collision}")
        shutil.copy2(art.path, dst)
        written.append(dst)
    return written
def build_manifest(outputs_dir: Path) -> Dict[str, object]:
    outputs_dir = Path(outputs_dir)
    files: List[Dict[str, object]] = []
    for p in sorted([x for x in outputs_dir.rglob("*") if x.is_file()]):
        rel = str(p.relative_to(outputs_dir)).replace("\\", "/")
        st = p.stat()
        files.append({
            "path": rel,
            "bytes": int(st.st_size),
            "mtime_utc": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
            "sha256": sha256_file(p),
        })
    return {"generated_utc": datetime.now(tz=timezone.utc).isoformat(), "count": len(files), "files": files}
def write_manifest(outputs_dir: Path, manifest_path: Optional[Path] = None) -> Path:
    outputs_dir = Path(outputs_dir)
    mp = Path(manifest_path) if manifest_path else (outputs_dir / "manifest.json")
    data = build_manifest(outputs_dir)
    mp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return mp
def write_index_md(outputs_dir: Path, manifest: Optional[Dict[str, object]] = None, index_path: Optional[Path] = None) -> Path:
    outputs_dir = Path(outputs_dir)
    ip = Path(index_path) if index_path else (outputs_dir / "index.md")
    m = manifest or build_manifest(outputs_dir)
    rows = ["# Outputs", "", f"Generated: `{m['generated_utc']}`", "", f"Files: `{m['count']}`", "", "| File | Bytes | SHA256 |", "|---|---:|---|"]
    for f in m["files"]:
        rows.append(f"| `{f['path']}` | {f['bytes']} | `{f['sha256']}` |")
    ip.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return ip
def consolidate_outputs(
    *,
    repo_root: Path,
    source_roots: Iterable[Path],
    outputs_dirname: str = "outputs",
    include: Optional[re.Pattern] = None,
    exclude: Optional[re.Pattern] = None,
    flatten: bool = False,
) -> Dict[str, object]:
    repo_root = Path(repo_root)
    outdir = repo_root / outputs_dirname
    artifacts = discover_artifacts(source_roots, include=include, exclude=exclude)
    selected = select_best_by_key(artifacts)
    copied = copy_artifacts(selected, outdir, flatten=flatten)
    manifest = build_manifest(outdir)
    write_manifest(outdir, outdir / "manifest.json")
    write_index_md(outdir, manifest=manifest, index_path=outdir / "index.md")
    return {"outputs_dir": str(outdir), "discovered": len(artifacts), "selected": len(selected), "copied": len(copied)}
