from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import os
import subprocess
from typing import Optional, Dict, Any, Iterable


def _run(cmd: Iterable[str], cwd: Path, timeout: float = 2.0) -> Optional[str]:
    try:
        p = subprocess.run(
            list(cmd),
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=timeout,
            check=False,
        )
        if p.returncode != 0:
            return None
        return (p.stdout or "").strip()
    except Exception:
        return None


def _read_text(p: Path) -> Optional[str]:
    try:
        return p.read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        return None


def _find_repo_root(start: Path) -> Optional[Path]:
    start = start.resolve()
    if start.is_file():
        start = start.parent
    cur = start
    for _ in range(64):
        if (cur / ".git").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def _parse_gitdir(git_path: Path) -> Optional[Path]:
    if git_path.is_dir():
        return git_path
    txt = _read_text(git_path)
    if not txt:
        return None
    # .git can be a file containing: "gitdir: <path>"
    prefix = "gitdir:"
    if txt.lower().startswith(prefix):
        rel = txt[len(prefix) :].strip()
        gd = (git_path.parent / rel).resolve()
        return gd if gd.exists() else None
    return None


def _sha_from_gitdir(gitdir: Path) -> Optional[str]:
    head = _read_text(gitdir / "HEAD")
    if not head:
        return None
    if head.startswith("ref:"):
        ref = head.split(":", 1)[1].strip()
        ref_path = gitdir / ref
        sha = _read_text(ref_path)
        if sha:
            return sha
        packed = _read_text(gitdir / "packed-refs")
        if not packed:
            return None
        for line in packed.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("^"):
                continue
            parts = line.split()
            if len(parts) == 2 and parts[1] == ref:
                return parts[0]
        return None
    # detached HEAD contains the sha directly
    return head.strip() if head else None


def _branch_from_gitdir(gitdir: Path) -> Optional[str]:
    head = _read_text(gitdir / "HEAD")
    if not head or not head.startswith("ref:"):
        return None
    ref = head.split(":", 1)[1].strip()
    if ref.startswith("refs/heads/"):
        return ref[len("refs/heads/") :]
    return ref


@dataclass(frozen=True)
class GitInfo:
    sha: Optional[str] = None
    dirty: Optional[bool] = None
    branch: Optional[str] = None
    describe: Optional[str] = None
    source: str = "none"  # git/env/file/none

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def get_git_info(path: Optional[os.PathLike] = None) -> GitInfo:
    """Return GitInfo for the repository containing `path` (or CWD).

    Works even when `git` is unavailable by falling back to reading .git metadata
    or environment variables commonly set in CI.
    """
    base = Path(path) if path is not None else Path.cwd()

    # 1) Environment fallbacks (CI)
    env_sha = (
        os.environ.get("GIT_SHA")
        or os.environ.get("GITHUB_SHA")
        or os.environ.get("CI_COMMIT_SHA")
        or os.environ.get("BUILD_VCS_NUMBER")
    )
    env_dirty = os.environ.get("GIT_DIRTY")
    if env_sha:
        dirty_val: Optional[bool] = None
        if env_dirty is not None:
            dirty_val = env_dirty.strip().lower() in {"1", "true", "yes", "y"}
        return GitInfo(
            sha=env_sha.strip(),
            dirty=dirty_val,
            branch=os.environ.get("GIT_BRANCH") or os.environ.get("GITHUB_REF_NAME"),
            describe=os.environ.get("GIT_DESCRIBE"),
            source="env",
        )

    # 2) Try git CLI
    repo = _find_repo_root(base)
    if repo:
        sha = _run(["git", "rev-parse", "HEAD"], cwd=repo)
        if sha:
            dirty_out = _run(["git", "status", "--porcelain"], cwd=repo)
            dirty = None if dirty_out is None else (dirty_out != "")
            branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo)
            if branch == "HEAD":
                branch = None
            describe = _run(["git", "describe", "--always", "--dirty"], cwd=repo)
            return GitInfo(
                sha=sha,
                dirty=dirty,
                branch=branch,
                describe=describe,
                source="git",
            )

        # 3) Read .git directly (works in exported artifacts with .git present)
        gitdir = _parse_gitdir(repo / ".git")
        if gitdir:
            sha2 = _sha_from_gitdir(gitdir)
            branch2 = _branch_from_gitdir(gitdir)
            return GitInfo(sha=sha2, dirty=None, branch=branch2, describe=None, source="file")

    return GitInfo()


def get_git_sha(path: Optional[os.PathLike] = None) -> Optional[str]:
    return get_git_info(path).sha
