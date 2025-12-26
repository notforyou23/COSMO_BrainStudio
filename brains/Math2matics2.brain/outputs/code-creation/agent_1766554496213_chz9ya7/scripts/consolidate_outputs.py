#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, shutil
from pathlib import Path
from datetime import datetime

def sha256_file(p: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(chunk_size), b""):
            h.update(b)
    return h.hexdigest()

def is_candidate_file(p: Path) -> bool:
    if not p.is_file():
        return False
    parts = {x.lower() for x in p.parts}
    s = str(p).lower()
    if "/.git/" in s or "/__pycache__/" in s:
        return False
    if "outputs" in parts and ("agent" in s or "runtime" in parts or "runs" in parts):
        return True
    if any(x.startswith("agent_") for x in p.parts):
        return True
    if "runtime" in parts and "outputs" in parts:
        return True
    if "artifacts" in parts and ("agent" in s or "run" in s):
        return True
    return False

def best_key(p: Path):
    st = p.stat()
    return (st.st_mtime, st.st_size)

def safe_rel(root: Path, p: Path) -> Path:
    try:
        return p.resolve().relative_to(root.resolve())
    except Exception:
        return Path("external") / p.name

def copy_file(src: Path, dst: Path, dry_run: bool) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dry_run:
        return
    shutil.copy2(src, dst)

def gather_sources(root: Path, out_dir: Path) -> list[Path]:
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        d = Path(dirpath)
        if d == out_dir or out_dir in d.parents:
            dirnames[:] = []
            continue
        low = str(d).lower()
        if "/.git" in low or "/__pycache__" in low:
            dirnames[:] = []
            continue
        for fn in filenames:
            p = d / fn
            if is_candidate_file(p):
                files.append(p)
    return files

def write_text(p: Path, text: str, dry_run: bool) -> None:
    if dry_run:
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")

def main() -> int:
    ap = argparse.ArgumentParser(description="Consolidate agent/run outputs into canonical ./outputs/")
    ap.add_argument("--root", default=".", help="Repo root to scan (default: cwd)")
    ap.add_argument("--outputs", default="outputs", help="Canonical outputs dir (repo-relative)")
    ap.add_argument("--dry-run", action="store_true", help="Scan and report without writing/copying")
    ap.add_argument("--limit", type=int, default=0, help="Max number of files to copy (0=unlimited)")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    out_dir = (root / args.outputs).resolve()
    artifacts_dir = out_dir / "artifacts"
    promoted_dir = out_dir / "promoted"

    sources = gather_sources(root, out_dir)
    sources = [p for p in sources if p.exists() and p.is_file()]
    sources.sort(key=lambda p: (str(p).lower(),) + tuple(best_key(p)))

    # Promote "best" per basename (mtime, then size)
    best_by_name: dict[str, Path] = {}
    for p in sources:
        name = p.name
        if name not in best_by_name or best_key(p) > best_key(best_by_name[name]):
            best_by_name[name] = p

    copied: list[dict] = []
    n = 0

    # Copy full tree under outputs/artifacts/<relative_source_path>
    for src in sources:
        rel = safe_rel(root, src)
        dst = artifacts_dir / rel
        if dst.exists():
            if best_key(src) <= best_key(dst):
                continue
        copy_file(src, dst, args.dry_run)
        n += 1
        if args.limit and n >= args.limit:
            break

    # Copy best-per-name under outputs/promoted/<filename>
    for name, src in sorted(best_by_name.items(), key=lambda kv: kv[0].lower()):
        dst = promoted_dir / name
        if dst.exists() and best_key(src) <= best_key(dst):
            continue
        copy_file(src, dst, args.dry_run)

    # Build manifest from everything now under outputs/
    manifest_items = []
    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
    for p in sorted([x for x in out_dir.rglob("*") if x.is_file()], key=lambda x: str(x).lower()):
        rel = p.relative_to(root)
        h = sha256_file(p) if not args.dry_run else None
        st = p.stat() if p.exists() else None
        manifest_items.append({
            "path": rel.as_posix(),
            "sha256": h,
            "bytes": st.st_size if st else None,
            "mtime": datetime.utcfromtimestamp(st.st_mtime).isoformat() + "Z" if st else None,
        })

    index_lines = [
        "# Outputs Index",
        "",
        f"Generated: {datetime.utcnow().isoformat()}Z",
        "",
        "## Files",
        "",
        "| Path | Bytes | SHA256 |",
        "|---|---:|---|",
    ]
    for it in manifest_items:
        path = it["path"]
        b = it["bytes"] if it["bytes"] is not None else ""
        h = it["sha256"] if it["sha256"] else ""
        index_lines.append(f"| `{path}` | {b} | `{h}` |")
    index_lines.append("")

    write_text(out_dir / "index.md", "\n".join(index_lines) + "\n", args.dry_run)
    write_text(out_dir / "manifest.json", json.dumps({"generated_utc": datetime.utcnow().isoformat() + "Z", "files": manifest_items}, indent=2) + "\n", args.dry_run)

    if args.dry_run:
        print(f"DRY_RUN: scanned={len(sources)} candidates, best_names={len(best_by_name)}")
    else:
        print(f"OK: consolidated outputs to {out_dir}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
