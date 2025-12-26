#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Tuple

DEFAULT_OUTPUTS_DIR = Path("outputs")
DEFAULT_MANIFEST_PATH = DEFAULT_OUTPUTS_DIR / "golden_manifest.json"
HASH_ALG = "sha256"

@dataclass(frozen=True)
class FileMeta:
    sha256: str
    size: int

def _sha256_file(path: Path) -> Tuple[str, int]:
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
            size += len(chunk)
    return h.hexdigest(), size

def _norm_rel(p: Path) -> str:
    s = p.as_posix()
    if s.startswith("./"):
        s = s[2:]
    return s

def _load_manifest(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: manifest not found: {path}")
    except json.JSONDecodeError as e:
        raise SystemExit(f"ERROR: invalid JSON manifest {path}: {e}")

def _write_manifest(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

def _manifest_files(manifest: Dict[str, Any]) -> Dict[str, FileMeta]:
    files = manifest.get("files")
    if not isinstance(files, dict) or not files:
        raise SystemExit("ERROR: manifest must contain non-empty object: files")
    out: Dict[str, FileMeta] = {}
    for rel, meta in files.items():
        if not isinstance(rel, str) or not rel or rel.startswith("/") or ".." in Path(rel).parts:
            raise SystemExit(f"ERROR: invalid manifest path key: {rel!r}")
        if not isinstance(meta, dict):
            raise SystemExit(f"ERROR: invalid manifest entry for {rel!r}")
        sha = meta.get(HASH_ALG)
        size = meta.get("size")
        if not isinstance(sha, str) or len(sha) != 64:
            raise SystemExit(f"ERROR: invalid sha256 for {rel!r}")
        if not isinstance(size, int) or size < 0:
            raise SystemExit(f"ERROR: invalid size for {rel!r}")
        out[rel] = FileMeta(sha256=sha, size=size)
    return out

def _build_manifest(outputs_dir: Path, relpaths: Dict[str, FileMeta] | None = None) -> Dict[str, Any]:
    files: Dict[str, Any] = {}
    if relpaths is None:
        for p in sorted(outputs_dir.rglob("*")):
            if p.is_file():
                rel = _norm_rel(p.relative_to(outputs_dir))
                sha, size = _sha256_file(p)
                files[rel] = {HASH_ALG: sha, "size": size}
    else:
        for rel in sorted(relpaths.keys()):
            p = outputs_dir / rel
            if not p.is_file():
                raise SystemExit(f"ERROR: required artifact missing: {p}")
            sha, size = _sha256_file(p)
            files[rel] = {HASH_ALG: sha, "size": size}
    return {"hash_alg": HASH_ALG, "files": files}

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Validate pipeline artifacts under outputs/ via golden checksum manifest.")
    ap.add_argument("--outputs", type=Path, default=DEFAULT_OUTPUTS_DIR, help="Outputs directory (default: outputs/).")
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH, help="Golden manifest path.")
    ap.add_argument("--update-golden", action="store_true", help="Update/write the golden manifest from current outputs.")
    ap.add_argument("--strict-extra", action="store_true", help="Fail if outputs contains extra files not listed in manifest.")
    args = ap.parse_args(argv)

    outputs_dir = args.outputs
    manifest_path = args.manifest

    if not outputs_dir.exists() or not outputs_dir.is_dir():
        print(f"ERROR: outputs directory not found: {outputs_dir}", file=sys.stderr)
        return 2

    if args.update_golden:
        # If manifest exists, treat its keys as the required set; else capture all current outputs files.
        if manifest_path.exists():
            man = _load_manifest(manifest_path)
            required = _manifest_files(man)
            new_man = _build_manifest(outputs_dir, required)
        else:
            new_man = _build_manifest(outputs_dir, None)
        _write_manifest(manifest_path, new_man)
        print(f"OK: wrote manifest: {manifest_path}")
        return 0

    manifest = _load_manifest(manifest_path)
    if manifest.get("hash_alg") not in (None, HASH_ALG):
        print(f"ERROR: unsupported hash_alg in manifest: {manifest.get('hash_alg')}", file=sys.stderr)
        return 2

    required = _manifest_files(manifest)
    current = _build_manifest(outputs_dir, required)

    exp_files = manifest["files"]
    cur_files = current["files"]

    missing = [k for k in exp_files.keys() if k not in cur_files]
    if missing:
        print("ERROR: missing required artifacts:", file=sys.stderr)
        for k in missing:
            print(f" - {k}", file=sys.stderr)
        return 1

    changed = []
    for rel, exp in exp_files.items():
        cur = cur_files.get(rel, {})
        if exp.get(HASH_ALG) != cur.get(HASH_ALG) or exp.get("size") != cur.get("size"):
            changed.append(rel)

    if changed:
        print("ERROR: artifact checksums differ from golden:", file=sys.stderr)
        for rel in changed[:200]:
            e = exp_files[rel]
            c = cur_files[rel]
            print(f" - {rel}: exp({e.get(HASH_ALG)},{e.get('size')}) cur({c.get(HASH_ALG)},{c.get('size')})", file=sys.stderr)
        if len(changed) > 200:
            print(f" ... and {len(changed)-200} more", file=sys.stderr)
        return 1

    if args.strict_extra:
        extras = []
        for p in outputs_dir.rglob("*"):
            if p.is_file():
                rel = _norm_rel(p.relative_to(outputs_dir))
                if rel not in exp_files:
                    extras.append(rel)
        if extras:
            print("ERROR: extra output files not in golden manifest:", file=sys.stderr)
            for rel in extras[:200]:
                print(f" - {rel}", file=sys.stderr)
            if len(extras) > 200:
                print(f" ... and {len(extras)-200} more", file=sys.stderr)
            return 1

    print(f"OK: validated {len(exp_files)} artifacts against {manifest_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
