"""CI artifact verification: ensure runtime/_build exists and is non-empty.

Usage:
  python ci/verify_artifacts.py
  python ci/verify_artifacts.py --path runtime/_build --max-list 200
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple


DEFAULT_IGNORED_BASENAMES: Set[str] = {
    ".DS_Store",
    "Thumbs.db",
    ".gitkeep",
    ".gitignore",
    "desktop.ini",
}

DEFAULT_IGNORED_DIRNAMES: Set[str] = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}


def _repo_root() -> Path:
    # Assumes this file lives at <repo>/ci/verify_artifacts.py
    return Path(__file__).resolve().parents[1]


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Verify CI build artifacts are present and non-empty.")
    p.add_argument(
        "--path",
        default="runtime/_build",
        help="Artifacts directory path (relative to repo root unless absolute). Default: runtime/_build",
    )
    p.add_argument(
        "--max-list",
        type=int,
        default=120,
        help="Max number of files to print in inventory. Default: 120",
    )
    p.add_argument(
        "--ignore",
        action="append",
        default=[],
        help="Additional ignored basenames (repeatable). Example: --ignore .DS_Store",
    )
    p.add_argument(
        "--ignore-dir",
        action="append",
        default=[],
        help="Additional ignored directory names (repeatable). Example: --ignore-dir __pycache__",
    )
    return p.parse_args(argv)


def _is_ignored(path: Path, ignored_basenames: Set[str], ignored_dirnames: Set[str]) -> bool:
    name = path.name
    if name in ignored_basenames:
        return True
    parts = set(path.parts)
    if parts & ignored_dirnames:
        return True
    return False


def _iter_files(root: Path, ignored_basenames: Set[str], ignored_dirnames: Set[str]) -> Iterable[Path]:
    # Deterministic traversal for stable CI logs
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted([d for d in dirnames if d not in ignored_dirnames])
        for fn in sorted(filenames):
            p = Path(dirpath) / fn
            if _is_ignored(p, ignored_basenames, ignored_dirnames):
                continue
            yield p


def _summarize(files: List[Path], root: Path, max_list: int) -> Tuple[int, int, List[str]]:
    total_bytes = 0
    rels: List[str] = []
    for p in files:
        try:
            total_bytes += p.stat().st_size
        except OSError:
            # If a file disappears mid-run, still include it in listing without size.
            pass
        try:
            rels.append(str(p.relative_to(root)))
        except ValueError:
            rels.append(str(p))
    rels_sorted = sorted(rels)
    return len(files), total_bytes, rels_sorted[: max(0, max_list)]


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    repo = _repo_root()
    artifacts_dir = Path(args.path)
    if not artifacts_dir.is_absolute():
        artifacts_dir = repo / artifacts_dir
    artifacts_dir = artifacts_dir.resolve()

    ignored_basenames = set(DEFAULT_IGNORED_BASENAMES) | set(args.ignore or [])
    ignored_dirnames = set(DEFAULT_IGNORED_DIRNAMES) | set(args.ignore_dir or [])

    if not artifacts_dir.exists():
        print(f"ARTIFACTS_MISSING: {artifacts_dir}")
        return 2
    if not artifacts_dir.is_dir():
        print(f"ARTIFACTS_NOT_DIR: {artifacts_dir}")
        return 2

    files = list(_iter_files(artifacts_dir, ignored_basenames, ignored_dirnames))
    count, total_bytes, preview = _summarize(files, artifacts_dir, args.max_list)

    print(f"ARTIFACTS_DIR: {artifacts_dir}")
    print(f"ARTIFACTS_COUNT: {count}")
    print(f"ARTIFACTS_BYTES: {total_bytes}")
    if preview:
        print("ARTIFACTS_INVENTORY:")
        for r in preview:
            print(f" - {r}")
        if count > len(preview):
            print(f" - ... ({count - len(preview)} more)")
    else:
        print("ARTIFACTS_INVENTORY: (none)")

    if count <= 0:
        print("ARTIFACTS_EMPTY: runtime/_build contains no files (after ignores).")
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
