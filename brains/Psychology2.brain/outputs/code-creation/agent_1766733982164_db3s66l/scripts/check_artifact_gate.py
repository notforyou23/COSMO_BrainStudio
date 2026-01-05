#!/usr/bin/env python3
"""Standalone artifact gate checker.

Validates that required canonical artifact output paths exist exactly as defined in
config/artifact_gate_paths.json. Exits nonzero on any mismatch.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _eprint(msg: str) -> None:
    sys.stderr.write(msg + "\n")


def _load_config(cfg_path: Path) -> dict:
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERROR: missing config file: {cfg_path}")
    except json.JSONDecodeError as e:
        raise SystemExit(f"ERROR: invalid JSON in {cfg_path}: {e}")
    if isinstance(data, list):
        data = {"required_paths": data}
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: config must be an object or array: {cfg_path}")
    return data


def _normalize_rel(p: str) -> str:
    p = p.replace("\\", "/").strip()
    while "//" in p:
        p = p.replace("//", "/")
    if p.startswith("/"):
        raise ValueError(f"absolute path not allowed: {p}")
    if p in ("", "."):
        raise ValueError("empty path not allowed")
    parts = [x for x in p.split("/") if x not in ("", ".")]
    if any(x == ".." for x in parts):
        raise ValueError(f"parent traversal not allowed: {p}")
    return "/".join(parts)


def _collect_files(root: Path, rel_dir: str) -> set[str]:
    base = root / rel_dir
    if not base.exists():
        return set()
    files: set[str] = set()
    for p in base.rglob("*"):
        if p.is_file():
            files.add(p.relative_to(root).as_posix())
    return files


def main(argv: list[str]) -> int:
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[1]
    cfg_path = repo_root / "config" / "artifact_gate_paths.json"

    cfg = _load_config(cfg_path)
    required = cfg.get("required_paths")
    if not isinstance(required, list) or not required:
        _eprint(f"ERROR: required_paths must be a non-empty list in {cfg_path}")
        return 2

    enforce_no_extra = bool(cfg.get("enforce_no_extra", False))
    allowed: set[str] = set()
    errors: list[str] = []

    for raw in required:
        if not isinstance(raw, str):
            errors.append(f"invalid required path (not string): {raw!r}")
            continue
        try:
            rel = _normalize_rel(raw)
        except ValueError as e:
            errors.append(str(e))
            continue
        allowed.add(rel)
        full = repo_root / rel
        if not full.exists():
            errors.append(f"missing: {rel}")
        elif not full.is_file():
            errors.append(f"not a file: {rel}")
        elif rel.startswith("outputs/") and full.stat().st_size == 0:
            errors.append(f"empty file: {rel}")

    if enforce_no_extra:
        outputs_files = _collect_files(repo_root, "outputs")
        extras = sorted(p for p in outputs_files if p not in allowed)
        if extras:
            errors.append("unexpected outputs files (enforce_no_extra=true):")
            errors.extend([f"  extra: {p}" for p in extras])

    if errors:
        _eprint("ARTIFACT_GATE_FAIL")
        for e in errors:
            _eprint(e)
        return 1

    if os.environ.get("ARTIFACT_GATE_QUIET") not in ("1", "true", "TRUE"):
        sys.stdout.write("ARTIFACT_GATE_OK\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
