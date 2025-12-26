#!/usr/bin/env python3
\"\"\"Integrate agent-generated outputs into the canonical repo layout.

Reads tools/integration_map.yml (or .json) describing move/merge rules and applies
them with safety checks. Designed to be reproducible and CI-friendly.
\"\"\"

from __future__ import annotations

import argparse
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _load_map(path: Path) -> Dict[str, Any]:
    data: Any
    try:
        import yaml  # type: ignore
    except Exception:
        yaml = None
    if yaml is not None and path.suffix in {".yml", ".yaml"}:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"Integration map must be a dict, got: {type(data).__name__}")
    return data


def _rel(p: Path, root: Path) -> str:
    try:
        return str(p.resolve().relative_to(root.resolve()))
    except Exception:
        return str(p)


def _ensure_within(path: Path, root: Path, label: str) -> None:
    rp, rr = path.resolve(), root.resolve()
    if rp == rr or rr not in rp.parents:
        raise SystemExit(f"{label} must be within repo root: {path}")


def _iter_files(src: Path) -> Iterable[Path]:
    if src.is_file():
        yield src
    else:
        for p in sorted(src.rglob("*")):
            if p.is_file():
                yield p


def _should_skip(rel: str, exclude: List[str]) -> bool:
    return any(fnmatch.fnmatch(rel, pat) for pat in exclude)


@dataclass(frozen=True)
class Op:
    kind: str  # "move" or "copy"
    src: Path
    dst: Path


def _plan_rule(repo: Path, rule: Dict[str, Any]) -> List[Op]:
    src_pat = rule.get("src")
    dst = rule.get("dst")
    mode = (rule.get("mode") or "merge").lower()
    overwrite = bool(rule.get("overwrite", False))
    exclude = list(rule.get("exclude") or [])
    if not src_pat or not dst:
        raise SystemExit("Each rule requires 'src' and 'dst'")
    if mode not in {"merge", "move"}:
        raise SystemExit(f"Unsupported mode: {mode}")
    dst_root = (repo / dst).resolve()
    _ensure_within(dst_root, repo, "dst")
    ops: List[Op] = []
    matches = sorted((repo / ".").glob(str(src_pat)))
    if not matches:
        raise SystemExit(f"No matches for src pattern: {src_pat}")
    for src in matches:
        src = src.resolve()
        _ensure_within(src, repo, "src")
        if mode == "move" and len(matches) > 1:
            raise SystemExit("mode=move requires src to resolve to a single path")
        if src.is_file():
            rel = src.name
            if _should_skip(rel, exclude):
                continue
            dst_path = dst_root / rel if dst_root.is_dir() or str(dst).endswith("/") else dst_root
            ops.append(Op("move" if mode == "move" else "copy", src, dst_path))
        else:
            for f in _iter_files(src):
                rel = str(f.relative_to(src))
                if _should_skip(rel, exclude):
                    continue
                ops.append(Op("copy", f, dst_root / rel))
            if mode == "move":
                ops.append(Op("move", src, dst_root))
    # overwrite checks are enforced at apply time; keep plan deterministic
    return ops


def _apply_ops(repo: Path, ops: List[Op], dry_run: bool, overwrite: bool) -> None:
    for op in ops:
        _ensure_within(op.dst, repo, "dst")
        if op.kind == "copy":
            if op.dst.exists() and not overwrite:
                raise SystemExit(f"Refusing to overwrite existing path: {_rel(op.dst, repo)}")
            if dry_run:
                print(f"COPY  {_rel(op.src, repo)} -> {_rel(op.dst, repo)}")
                continue
            op.dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(op.src, op.dst)
        elif op.kind == "move":
            if op.dst.exists() and not overwrite:
                raise SystemExit(f"Refusing to overwrite existing path: {_rel(op.dst, repo)}")
            if dry_run:
                print(f"MOVE  {_rel(op.src, repo)} -> {_rel(op.dst, repo)}")
                continue
            op.dst.parent.mkdir(parents=True, exist_ok=True)
            if op.dst.exists() and overwrite:
                if op.dst.is_dir():
                    shutil.rmtree(op.dst)
                else:
                    op.dst.unlink()
            shutil.move(str(op.src), str(op.dst))
        else:
            raise SystemExit(f"Unknown op: {op.kind}")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--map", dest="map_path", default="tools/integration_map.yml")
    ap.add_argument("--repo", default=".", help="Repository root")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--overwrite", action="store_true", help="Allow overwriting destination paths")
    args = ap.parse_args(argv)

    repo = Path(args.repo).resolve()
    map_path = (repo / args.map_path).resolve()
    _ensure_within(map_path, repo, "map")
    spec = _load_map(map_path)
    rules = spec.get("rules") or []
    if not isinstance(rules, list) or not rules:
        raise SystemExit("integration_map must contain a non-empty 'rules' list")

    all_ops: List[Op] = []
    for rule in rules:
        if not isinstance(rule, dict):
            raise SystemExit("Each rule must be a dict")
        all_ops.extend(_plan_rule(repo, rule))

    # Apply in a stable order for reproducibility
    all_ops = sorted(all_ops, key=lambda o: (o.kind, str(o.src), str(o.dst)))

    _apply_ops(repo, all_ops, dry_run=args.dry_run, overwrite=args.overwrite)
    if args.dry_run:
        print(f\"Planned ops: {len(all_ops)}\")
    return 0


if __name__ == \"__main__\":
    raise SystemExit(main())
