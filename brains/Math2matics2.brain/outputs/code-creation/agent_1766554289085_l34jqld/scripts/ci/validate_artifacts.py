#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "files" not in data or not isinstance(data["files"], dict):
        raise ValueError(f"Invalid manifest format: {path}")
    algo = data.get("algorithm", "sha256")
    if algo != "sha256":
        raise ValueError(f"Unsupported algorithm in manifest: {algo}")
    return data


def compute_for_manifest(outputs_dir: Path, manifest: dict) -> dict:
    out = {"algorithm": "sha256", "root": str(manifest.get("root", "outputs")), "files": {}}
    for rel, expected in sorted(manifest["files"].items()):
        p = outputs_dir / rel
        if not p.is_file():
            raise FileNotFoundError(f"Missing required artifact: {p}")
        out["files"][rel] = sha256_file(p)
    return out


def compute_manifest_from_tree(outputs_dir: Path) -> dict:
    files = {}
    for p in sorted(outputs_dir.rglob("*")):
        if p.is_file():
            rel = p.relative_to(outputs_dir).as_posix()
            files[rel] = sha256_file(p)
    return {"algorithm": "sha256", "root": "outputs", "files": files}


def validate(outputs_dir: Path, manifest_path: Path, strict_extra: bool) -> int:
    if not outputs_dir.is_dir():
        print(f"ERROR: outputs dir not found: {outputs_dir}", file=sys.stderr)
        return 2
    if not manifest_path.is_file():
        print(f"ERROR: manifest not found: {manifest_path}", file=sys.stderr)
        return 2

    manifest = load_manifest(manifest_path)
    computed = compute_for_manifest(outputs_dir, manifest)

    missing = []
    mismatched = []
    for rel, expected in sorted(manifest["files"].items()):
        p = outputs_dir / rel
        if not p.is_file():
            missing.append(rel)
            continue
        got = computed["files"].get(rel)
        if got != expected:
            mismatched.append((rel, expected, got))

    extras = []
    if strict_extra:
        expected_set = set(manifest["files"].keys())
        for p in outputs_dir.rglob("*"):
            if p.is_file():
                rel = p.relative_to(outputs_dir).as_posix()
                if rel not in expected_set:
                    extras.append(rel)

    if missing or mismatched or extras:
        if missing:
            print("MISSING_ARTIFACTS:", file=sys.stderr)
            for rel in missing:
                print(f"  {rel}", file=sys.stderr)
        if mismatched:
            print("CHECKSUM_MISMATCH:", file=sys.stderr)
            for rel, exp, got in mismatched:
                print(f"  {rel}", file=sys.stderr)
                print(f"    expected: {exp}", file=sys.stderr)
                print(f"    got:      {got}", file=sys.stderr)
        if extras:
            print("UNEXPECTED_ARTIFACTS:", file=sys.stderr)
            for rel in extras:
                print(f"  {rel}", file=sys.stderr)
        return 1

    print(f"OK: validated {len(manifest['files'])} artifacts against {manifest_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate required outputs artifacts against a golden checksum manifest.")
    ap.add_argument("--repo-root", default=".", help="Repository root (default: .)")
    ap.add_argument("--outputs", default="outputs", help="Outputs directory relative to repo root (default: outputs)")
    ap.add_argument("--manifest", default="outputs/golden_manifest.json", help="Manifest path relative to repo root")
    ap.add_argument("--strict-extra", action="store_true", help="Fail if outputs contains files not listed in manifest")
    ap.add_argument("--update", action="store_true", help="Write/update manifest from current outputs tree")
    args = ap.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    outputs_dir = (repo_root / args.outputs).resolve()
    manifest_path = (repo_root / args.manifest).resolve()

    if args.update:
        if not outputs_dir.is_dir():
            print(f"ERROR: outputs dir not found: {outputs_dir}", file=sys.stderr)
            return 2
        manifest = compute_manifest_from_tree(outputs_dir)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"UPDATED_MANIFEST: {manifest_path} ({len(manifest['files'])} files)")
        return 0

    return validate(outputs_dir, manifest_path, bool(args.strict_extra))


if __name__ == "__main__":
    raise SystemExit(main())
