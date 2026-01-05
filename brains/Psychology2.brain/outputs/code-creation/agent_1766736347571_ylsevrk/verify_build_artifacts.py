#!/usr/bin/env python3
\"\"\"verify_build_artifacts.py

Command-line tool to verify that required build artifacts exist under runtime/_build
and that every matched artifact is non-empty. Exits non-zero with clear diagnostics
if requirements are not met.

Typical usage:
  python verify_build_artifacts.py
  python verify_build_artifacts.py --root runtime/_build
\"\"\"

from __future__ import annotations

import argparse
import sys
from pathlib import Path


DEFAULT_REQUIRED_GLOBS = (
    "reports/*.json",
    "tables/*.csv",
    "figures/*",
)


def _iter_matches(root: Path, pattern: str) -> list[Path]:
    # Use glob relative to root; pattern uses forward slashes; Path.glob supports that cross-platform.
    matches = sorted(root.glob(pattern))
    # Filter out directories (e.g., figures subfolders) – we validate files only.
    return [p for p in matches if p.is_file()]


def _format_paths(paths: list[Path], root: Path) -> str:
    def rel(p: Path) -> str:
        try:
            return str(p.relative_to(root))
        except Exception:
            return str(p)
    return "\\n".join(f"  - {rel(p)}" for p in paths)


def verify_artifacts(root: Path, required_globs: list[str]) -> int:
    missing_patterns: list[str] = []
    empty_files: list[Path] = []
    matched_by_pattern: dict[str, list[Path]] = {}

    if not root.exists():
        sys.stderr.write(f"ERROR: Build artifacts root does not exist: {root}\\n")
        return 2
    if not root.is_dir():
        sys.stderr.write(f"ERROR: Build artifacts root is not a directory: {root}\\n")
        return 2

    for pat in required_globs:
        matches = _iter_matches(root, pat)
        matched_by_pattern[pat] = matches
        if not matches:
            missing_patterns.append(pat)
            continue
        for p in matches:
            try:
                size = p.stat().st_size
            except FileNotFoundError:
                empty_files.append(p)
                continue
            if size <= 0:
                empty_files.append(p)

    if missing_patterns or empty_files:
        sys.stderr.write("BUILD ARTIFACT VERIFICATION FAILED\\n")
        sys.stderr.write(f"Root: {root}\\n")
        if missing_patterns:
            sys.stderr.write("\\nMissing required artifact patterns (no matching files):\\n")
            for pat in missing_patterns:
                sys.stderr.write(f"  - {pat}\\n")
        sys.stderr.write("\\nPattern match summary:\\n")
        for pat in required_globs:
            matches = matched_by_pattern.get(pat, [])
            sys.stderr.write(f"  {pat}: {len(matches)} file(s)\\n")
        if empty_files:
            sys.stderr.write("\\nEmpty (or unreadable) artifact files:\\n")
            sys.stderr.write(_format_paths(sorted(set(empty_files)), root) + "\\n")
        sys.stderr.write("\\nTo fix: ensure the build pipeline writes these artifacts under runtime/_build and that files are non-empty.\\n")
        return 2

    sys.stdout.write("BUILD ARTIFACT VERIFICATION PASSED\\n")
    sys.stdout.write(f"Root: {root}\\n")
    for pat in required_globs:
        sys.stdout.write(f"  {pat}: {len(matched_by_pattern.get(pat, []))} file(s)\\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify required build artifacts exist and are non-empty under runtime/_build."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("runtime") / "_build",
        help="Build artifacts root directory (default: runtime/_build)",
    )
    parser.add_argument(
        "--require",
        action="append",
        default=None,
        help="Additional required glob pattern under --root (may be specified multiple times).",
    )
    parser.add_argument(
        "--no-defaults",
        action="store_true",
        help="Do not include default required patterns; only use --require patterns.",
    )

    ns = parser.parse_args(argv)
    root = ns.root

    required = []
    if not ns.no_defaults:
        required.extend(DEFAULT_REQUIRED_GLOBS)
    if ns.require:
        required.extend(ns.require)

    if not required:
        sys.stderr.write("ERROR: No required patterns specified (use defaults or pass --require).\\n")
        return 2

    return verify_artifacts(root=root, required_globs=required)


if __name__ == "__main__":
    raise SystemExit(main())
