#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


DEFAULT_REQUIREMENTS = [
    {"name": "json_report", "dir": "runtime/_build/reports", "exts": [".json"], "min_count": 1},
    {"name": "csv_table", "dir": "runtime/_build/tables", "exts": [".csv"], "min_count": 1},
    {"name": "figure", "dir": "runtime/_build/figures", "exts": [".png", ".pdf"], "min_count": 1},
    {"name": "log", "dir": "runtime/_build/logs", "exts": [".log"], "min_count": 1},
]


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    return here.parent.parent


def _load_config(path: Path | None) -> list[dict]:
    if not path:
        return DEFAULT_REQUIREMENTS
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return DEFAULT_REQUIREMENTS
    if isinstance(data, dict) and isinstance(data.get("requirements"), list):
        reqs = data["requirements"]
    elif isinstance(data, list):
        reqs = data
    else:
        return DEFAULT_REQUIREMENTS
    out = []
    for r in reqs:
        if not isinstance(r, dict):
            continue
        name = str(r.get("name") or r.get("dir") or "requirement")
        d = str(r.get("dir") or "")
        exts = r.get("exts") or r.get("extensions") or []
        if isinstance(exts, str):
            exts = [exts]
        exts = [e if e.startswith(".") else f".{e}" for e in exts if isinstance(e, str) and e]
        min_count = int(r.get("min_count", r.get("minCount", 1)) or 1)
        if d and exts:
            out.append({"name": name, "dir": d, "exts": exts, "min_count": min_count})
    return out or DEFAULT_REQUIREMENTS


def _iter_matching_files(dir_path: Path, exts: list[str], recursive: bool = True):
    if not dir_path.exists() or not dir_path.is_dir():
        return []
    it = dir_path.rglob("*") if recursive else dir_path.glob("*")
    exts_l = {e.lower() for e in exts}
    files = []
    for p in it:
        if p.is_file() and p.suffix.lower() in exts_l:
            try:
                if p.stat().st_size > 0:
                    files.append(p)
            except OSError:
                continue
    return sorted(files, key=lambda x: x.as_posix())


def _rel(p: Path, root: Path) -> str:
    try:
        return str(p.resolve().relative_to(root.resolve()))
    except Exception:
        return str(p)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Verify runtime/_build contains required non-empty artifact outputs."
    )
    ap.add_argument(
        "--root",
        default=None,
        help="Repository root (defaults to parent of scripts/).",
    )
    ap.add_argument(
        "--config",
        default=None,
        help="Optional JSON config file describing requirements; if missing, built-in defaults are used.",
    )
    ap.add_argument(
        "--no-recursive",
        action="store_true",
        help="Do not scan artifact directories recursively.",
    )
    args = ap.parse_args(argv)

    root = Path(args.root).resolve() if args.root else _repo_root()
    cfg_path = Path(args.config).resolve() if args.config else root / "scripts" / "verify_build_artifacts.json"
    reqs = _load_config(cfg_path if args.config or cfg_path.exists() else None)

    missing = []
    found_summary = []

    for r in reqs:
        dir_path = (root / r["dir"]).resolve()
        files = _iter_matching_files(dir_path, r["exts"], recursive=not args.no_recursive)
        if len(files) < int(r.get("min_count", 1)):
            missing.append(
                {
                    "name": r["name"],
                    "dir": _rel(dir_path, root),
                    "extensions": r["exts"],
                    "min_count": int(r.get("min_count", 1)),
                    "found": [_rel(p, root) for p in files],
                }
            )
        else:
            found_summary.append(
                {
                    "name": r["name"],
                    "dir": _rel(dir_path, root),
                    "count": len(files),
                    "examples": [_rel(p, root) for p in files[:3]],
                }
            )

    if missing:
        sys.stderr.write("ARTIFACT_VERIFICATION_FAILED\n")
        sys.stderr.write(f"root={root.as_posix()}\n")
        sys.stderr.write("missing_requirements:\n")
        for m in missing:
            sys.stderr.write(
                f"  - {m['name']}: need>={m['min_count']} non-empty in {m['dir']} (ext={','.join(m['extensions'])}) found={len(m['found'])}\n"
            )
            if m["found"]:
                for fp in m["found"]:
                    sys.stderr.write(f"      found: {fp}\n")
        return 2

    sys.stdout.write("ARTIFACT_VERIFICATION_OK\n")
    sys.stdout.write(f"root={root.as_posix()}\n")
    for s in sorted(found_summary, key=lambda x: (x["dir"], x["name"])):
        ex = f" examples={','.join(s['examples'])}" if s["examples"] else ""
        sys.stdout.write(f"  - {s['name']}: {s['count']} in {s['dir']}{ex}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
