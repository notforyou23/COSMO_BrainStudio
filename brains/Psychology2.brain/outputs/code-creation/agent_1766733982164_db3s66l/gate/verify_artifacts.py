#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


DEFAULT_PATTERNS = [
    "runtime/_build/reports/*.json",
    "runtime/_build/tables/*.csv",
    "runtime/_build/logs/*.jsonl",
]


def _repo_root_from_this_file(this_file: Path) -> Path:
    # gate/verify_artifacts.py -> repo root is parent of gate/
    return this_file.resolve().parents[1]


def _fmt_list(items: list[str], indent: str = "  - ") -> str:
    return "\n".join(f"{indent}{x}" for x in items)


def verify(root: Path, patterns: list[str]) -> tuple[int, str]:
    missing_patterns: list[str] = []
    empty_files: list[str] = []
    bad_paths: list[str] = []
    checked_files = 0

    for pat in patterns:
        matches = sorted(root.glob(pat))
        if not matches:
            missing_patterns.append(pat)
            continue
        for p in matches:
            if not p.exists():
                bad_paths.append(str(p))
                continue
            if p.is_dir():
                bad_paths.append(f"{p} (is a directory)")
                continue
            checked_files += 1
            try:
                if p.stat().st_size <= 0:
                    empty_files.append(str(p.relative_to(root)))
            except OSError as e:
                bad_paths.append(f"{p} (stat failed: {e})")

    if missing_patterns or empty_files or bad_paths:
        lines = ["ARTIFACT_VERIFICATION_FAILED"]
        lines.append(f"Root: {root}")
        lines.append(f"Patterns checked: {len(patterns)}; Files matched: {checked_files}")
        if missing_patterns:
            lines.append("Missing (no matches for glob patterns):")
            lines.append(_fmt_list(missing_patterns))
        if empty_files:
            lines.append("Empty (matched but size==0):")
            lines.append(_fmt_list(empty_files))
        if bad_paths:
            lines.append("Invalid (unexpected path types or errors):")
            lines.append(_fmt_list(bad_paths))
        return 1, "\n".join(lines) + "\n"

    return 0, f"ARTIFACT_VERIFICATION_OK\nRoot: {root}\nPatterns checked: {len(patterns)}; Files matched: {checked_files}\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Gate that verifies required build artifacts exist and are non-empty.")
    ap.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root (defaults to parent of gate/).",
    )
    ap.add_argument(
        "--pattern",
        action="append",
        default=[],
        help="Glob pattern relative to root; can be repeated.",
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Also fail if no files matched at all across all patterns (in addition to per-pattern missing).",
    )

    args = ap.parse_args(argv)
    root = args.root if args.root is not None else _repo_root_from_this_file(Path(__file__))
    patterns = args.pattern if args.pattern else list(DEFAULT_PATTERNS)

    code, msg = verify(root=root, patterns=patterns)
    sys.stderr.write(msg if code else "")
    sys.stdout.write("" if code else msg)

    if args.strict and code == 0:
        total = sum(1 for pat in patterns for _ in root.glob(pat))
        if total == 0:
            sys.stderr.write("ARTIFACT_VERIFICATION_FAILED\nNo artifacts matched any pattern under root.\n")
            return 1

    return code


if __name__ == "__main__":
    raise SystemExit(main())
