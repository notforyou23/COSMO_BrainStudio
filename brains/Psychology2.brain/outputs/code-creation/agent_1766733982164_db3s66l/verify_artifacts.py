#!/usr/bin/env python3
"""
verify_artifacts.py

Command-line verifier that checks a build output directory for required non-empty outputs.
Intended for CI gating: exits nonzero if any required artifact is missing or empty.

Configuration:
- --build-dir PATH (default: runtime/_build)
- --require PATH (repeatable) relative to build dir unless absolute
- env REQUIRED_ARTIFACTS: comma/semicolon/newline-separated list of required paths
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _split_required(s: str) -> list[str]:
    parts: list[str] = []
    for sep in [",", ";", "\n"]:
        if sep in s:
            tmp: list[str] = []
            for p in (x.strip() for x in s.split(sep)):
                if p:
                    tmp.append(p)
            s = ",".join(tmp)
    for p in (x.strip() for x in s.split(",") if x.strip()):
        parts.append(p)
    return parts


def _is_nonempty_file(p: Path) -> bool:
    try:
        return p.is_file() and p.stat().st_size > 0
    except OSError:
        return False


def _dir_has_nonempty_files(d: Path) -> bool:
    try:
        if not d.is_dir():
            return False
        for x in d.rglob("*"):
            if x.is_file():
                try:
                    if x.stat().st_size > 0:
                        return True
                except OSError:
                    continue
        return False
    except OSError:
        return False


def verify(build_dir: Path, required: list[str]) -> tuple[list[str], list[str]]:
    missing: list[str] = []
    empty: list[str] = []

    for item in required:
        raw = item.strip()
        if not raw:
            continue
        p = Path(raw)
        path = p if p.is_absolute() else (build_dir / p)
        if not path.exists():
            missing.append(raw)
            continue
        if path.is_dir():
            if not _dir_has_nonempty_files(path):
                empty.append(raw)
        else:
            if not _is_nonempty_file(path):
                empty.append(raw)

    return missing, empty


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verify required non-empty build artifacts exist.")
    ap.add_argument("--build-dir", default="runtime/_build", help="Build output directory (default: runtime/_build)")
    ap.add_argument(
        "--require",
        action="append",
        default=[],
        help="Required artifact path under build dir (repeatable). Can be a file or directory.",
    )
    ap.add_argument(
        "--require-env",
        default="REQUIRED_ARTIFACTS",
        help="Env var containing required artifact paths (default: REQUIRED_ARTIFACTS)",
    )
    ap.add_argument("--allow-empty-requirements", action="store_true", help="Succeed if no requirements are provided.")
    ap.add_argument("--quiet", action="store_true", help="Only print failures.")
    args = ap.parse_args(argv)

    build_dir = Path(args.build_dir).resolve()
    required = list(args.require or [])

    env_name = args.require_env
    env_val = os.environ.get(env_name, "").strip()
    if env_val:
        required.extend(_split_required(env_val))

    required = [r for r in required if r and r.strip()]
    if not required and not args.allow_empty_requirements:
        print(
            f"ERROR: No required artifacts specified. Provide --require or set {env_name}.",
            file=sys.stderr,
        )
        return 3

    missing, empty = verify(build_dir, required)

    if missing or empty:
        if not args.quiet:
            print(f"Build dir: {build_dir}", file=sys.stderr)
            print(f"Required ({len(required)}): " + ", ".join(required), file=sys.stderr)
        if missing:
            print("MISSING:", file=sys.stderr)
            for m in missing:
                print(f"  - {m}", file=sys.stderr)
        if empty:
            print("EMPTY:", file=sys.stderr)
            for e in empty:
                print(f"  - {e}", file=sys.stderr)
        return 2

    if not args.quiet:
        print(f"OK: {len(required)} required artifacts present and non-empty under {build_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
