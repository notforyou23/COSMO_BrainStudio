#!/usr/bin/env python3
"""verify_build_artifacts.py

Command-line verification tool that asserts required build artifact file patterns
exist under runtime/_build and that each matched file is non-empty.

Exits non-zero with clear diagnostics if validation fails.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple


DEFAULT_PATTERNS: Tuple[str, ...] = (
    "reports/*.json",
    "tables/*.csv",
    "figures/*",
)


@dataclass(frozen=True)
class MatchResult:
    pattern: str
    matches: Tuple[Path, ...]


def _iter_matches(root: Path, pattern: str) -> Tuple[Path, ...]:
    # Use glob for patterns like "reports/*.json"; allow ** as well if supplied.
    paths = tuple(sorted(root.glob(pattern)))
    return paths


def _is_nonempty_file(p: Path) -> bool:
    try:
        if not p.is_file():
            return False
        return p.stat().st_size > 0
    except OSError:
        return False


def _validate_patterns(root: Path, patterns: Sequence[str]) -> Tuple[List[str], List[Path], List[Path]]:
    missing_patterns: List[str] = []
    empty_files: List[Path] = []
    nonfile_matches: List[Path] = []

    for pat in patterns:
        matches = _iter_matches(root, pat)
        if not matches:
            missing_patterns.append(pat)
            continue

        for m in matches:
            if not m.exists():
                continue
            if m.is_dir():
                # For directory matches (e.g., figures/*), treat as non-file match.
                # We'll accept directories only if they contain at least one non-empty file.
                # Record it for diagnostics; actual failure depends on content below.
                nonfile_matches.append(m)
                continue
            if not _is_nonempty_file(m):
                empty_files.append(m)

        # Special handling: if a pattern matches only directories, ensure those dirs contain non-empty files.
        file_matches = [m for m in matches if m.exists() and m.is_file()]
        if not file_matches:
            # All matches are non-files; require at least one non-empty file under those dirs.
            found_nonempty = False
            for d in (m for m in matches if m.exists() and m.is_dir()):
                for fp in d.rglob("*"):
                    if _is_nonempty_file(fp):
                        found_nonempty = True
                        break
                if found_nonempty:
                    break
            if not found_nonempty:
                missing_patterns.append(pat)

    return missing_patterns, empty_files, nonfile_matches


def _rel(p: Path, base: Path) -> str:
    try:
        return str(p.relative_to(base))
    except Exception:
        return str(p)


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Verify required build artifacts exist under runtime/_build and are non-empty.",
    )
    ap.add_argument(
        "--root",
        default=str(Path("runtime") / "_build"),
        help="Build artifacts root directory (default: runtime/_build).",
    )
    ap.add_argument(
        "--pattern",
        action="append",
        default=[],
        help="Glob pattern relative to root. May be repeated. If not provided, defaults are used.",
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Fail if patterns match directories (e.g., figures/*). Still requires non-empty files either way.",
    )
    ap.add_argument(
        "--list",
        action="store_true",
        help="List matched files and exit 0 (still validates).",
    )
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    root = Path(args.root)

    patterns = tuple(args.pattern) if args.pattern else DEFAULT_PATTERNS

    if not root.exists():
        print(f"ERROR: artifacts root not found: {root}", file=sys.stderr)
        return 2
    if not root.is_dir():
        print(f"ERROR: artifacts root is not a directory: {root}", file=sys.stderr)
        return 2

    missing_patterns, empty_files, nonfile_matches = _validate_patterns(root, patterns)

    if args.strict and nonfile_matches:
        print("ERROR: strict mode: patterns matched non-file paths:", file=sys.stderr)
        for p in sorted(set(nonfile_matches)):
            print(f"  - {_rel(p, root)}", file=sys.stderr)
        return 2

    # Optional listing of matches for audit friendliness.
    if args.list:
        print(f"ARTIFACT_ROOT: {root}")
        for pat in patterns:
            matches = _iter_matches(root, pat)
            print(f"PATTERN: {pat}")
            for m in matches:
                tag = "DIR" if m.is_dir() else "FILE"
                size = ""
                if m.is_file():
                    try:
                        size = f" ({m.stat().st_size} bytes)"
                    except OSError:
                        size = ""
                print(f"  - {tag}: {_rel(m, root)}{size}")

    if not missing_patterns and not empty_files:
        print("OK: build artifacts verified")
        return 0

    print("ERROR: build artifact verification failed", file=sys.stderr)

    if missing_patterns:
        print("Missing required artifact patterns (no acceptable non-empty files found):", file=sys.stderr)
        for pat in missing_patterns:
            print(f"  - {pat}", file=sys.stderr)

    if empty_files:
        print("Empty or unreadable files:", file=sys.stderr)
        for p in sorted(set(empty_files)):
            print(f"  - {_rel(p, root)}", file=sys.stderr)

    # Provide quick hint on where we looked.
    print(f"Artifacts root checked: {root}", file=sys.stderr)
    print("To customize, pass --root and/or one or more --pattern arguments.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
