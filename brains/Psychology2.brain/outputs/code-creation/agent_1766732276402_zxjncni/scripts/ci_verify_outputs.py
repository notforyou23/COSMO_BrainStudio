#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _repo_root_from_this_file() -> Path:
    here = Path(__file__).resolve()
    # scripts/ci_verify_outputs.py -> repo root is parent of scripts/
    return here.parent.parent


def _parse_required_from_env() -> list[str]:
    raw = os.environ.get("CI_REQUIRED_OUTPUTS", "").strip()
    if not raw:
        return []
    # Accept JSON list or comma/space-separated
    if raw[:1] in "[{":
        try:
            obj = json.loads(raw)
        except Exception as e:
            raise SystemExit(f"ERROR: CI_REQUIRED_OUTPUTS is not valid JSON: {e}")
        if isinstance(obj, dict) and "paths" in obj:
            obj = obj["paths"]
        if not isinstance(obj, list) or not all(isinstance(x, str) for x in obj):
            raise SystemExit("ERROR: CI_REQUIRED_OUTPUTS JSON must be a list of strings (or {\"paths\": [...]})")
        return [s.strip() for s in obj if s.strip()]
    parts = [p.strip() for p in raw.replace("\n", ",").replace(" ", ",").split(",")]
    return [p for p in parts if p]


def _is_nonempty_dir(p: Path) -> bool:
    try:
        return p.is_dir() and any(p.iterdir())
    except Exception:
        return False


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="CI helper: hard-fail if required outputs are missing.")
    ap.add_argument("--root", default=None, help="Repo root to resolve relative paths (default: inferred).")
    ap.add_argument("--require", action="append", default=[], help="Required output path (relative to root unless absolute). Repeatable.")
    ap.add_argument("--require-nonempty-dir", action="append", default=[], help="Required directory that must exist and be non-empty.")
    ap.add_argument("--json", dest="json_out", action="store_true", help="Emit JSON summary to stdout.")
    ns = ap.parse_args(argv)

    root = Path(ns.root).resolve() if ns.root else _repo_root_from_this_file()

    required = list(ns.require)
    required_nonempty = list(ns.require_nonempty_dir)

    env_required = _parse_required_from_env()
    if env_required:
        required.extend(env_required)

    # Defaults: ensure runtime/_build exists; keep additional requirements light/minimal.
    if not required and not required_nonempty:
        required = ["runtime/_build"]

    missing: list[str] = []
    missing_nonempty: list[str] = []
    checked: list[str] = []

    def resolve_path(s: str) -> Path:
        p = Path(s)
        return p if p.is_absolute() else (root / p)

    for s in required:
        p = resolve_path(s)
        checked.append(str(p))
        if not p.exists():
            missing.append(s)

    for s in required_nonempty:
        p = resolve_path(s)
        checked.append(str(p))
        if not _is_nonempty_dir(p):
            missing_nonempty.append(s)

    ok = not missing and not missing_nonempty
    summary = {
        "ok": ok,
        "root": str(root),
        "checked": checked,
        "missing": missing,
        "missing_nonempty_dir": missing_nonempty,
    }

    if ns.json_out:
        print(json.dumps(summary, indent=2, sort_keys=True))

    if not ok:
        sys.stderr.write("ERROR: Required CI outputs missing.\n")
        if missing:
            sys.stderr.write("  Missing paths:\n" + "".join(f"    - {m}\n" for m in missing))
        if missing_nonempty:
            sys.stderr.write("  Missing/empty required directories:\n" + "".join(f"    - {m}\n" for m in missing_nonempty))
        sys.stderr.write(f"  Root: {root}\n")
        return 2

    if not ns.json_out:
        print("OK: required outputs present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
