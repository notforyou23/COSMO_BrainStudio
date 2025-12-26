"""Install repository git hooks.

Copies support/githooks/pre-commit into .git/hooks/pre-commit and ensures it is executable.

Usage:
  python support/install_githooks.py [--force]
"""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import sys
from pathlib import Path
def _find_repo_root(start: Path) -> Path:
    start = start.resolve()
    for p in (start, *start.parents):
        if (p / ".git").exists():
            return p
    raise FileNotFoundError("Could not find repository root (no .git directory found).")
def _read_bytes(p: Path) -> bytes:
    return p.read_bytes()


def _ensure_executable(path: Path) -> None:
    try:
        mode = path.stat().st_mode
        mode |= stat.S_IXUSR
        mode |= stat.S_IXGRP
        mode |= stat.S_IXOTH
        os.chmod(path, mode)
    except OSError:
        # Best-effort; some filesystems may not support chmod.
        pass
def install_pre_commit_hook(repo_root: Path, force: bool = False) -> Path:
    src = repo_root / "support" / "githooks" / "pre-commit"
    if not src.is_file():
        raise FileNotFoundError(f"Missing hook source file: {src}")

    git_dir = repo_root / ".git"
    if not git_dir.exists():
        raise FileNotFoundError(f"Missing .git directory: {git_dir}")

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    dst = hooks_dir / "pre-commit"

    if dst.exists() and not force:
        if _read_bytes(dst) == _read_bytes(src):
            _ensure_executable(dst)
            return dst
        raise FileExistsError(f"Hook already exists and differs: {dst} (use --force to overwrite)")

    shutil.copyfile(src, dst)
    _ensure_executable(dst)
    return dst
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install repository git hooks.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing hooks.")
    args = parser.parse_args(argv)

    try:
        repo_root = _find_repo_root(Path(__file__).parent)
        dst = install_pre_commit_hook(repo_root, force=args.force)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    print(f"Installed pre-commit hook: {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
