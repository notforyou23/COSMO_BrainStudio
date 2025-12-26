from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Optional, Sequence, Union, Dict, Any
PathLike = Union[str, Path]


@dataclass(frozen=True)
class GitInfo:
    commit: Optional[str] = None
    branch: Optional[str] = None
    is_dirty: Optional[bool] = None
    describe: Optional[str] = None
    repo_root: Optional[str] = None
def _run_git(args: Sequence[str], cwd: Optional[PathLike]) -> Optional[str]:
    try:
        p = subprocess.run(
            ["git", *args],
            cwd=str(cwd) if cwd is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except Exception:
        return None
    if p.returncode != 0:
        return None
    out = (p.stdout or "").strip()
    return out if out else None
def _git_repo_root(cwd: Optional[PathLike] = None) -> Optional[str]:
    out = _run_git(["rev-parse", "--show-toplevel"], cwd=cwd)
    return out
def is_git_repo(cwd: Optional[PathLike] = None) -> bool:
    return _git_repo_root(cwd=cwd) is not None
def get_commit_hash(cwd: Optional[PathLike] = None, short: bool = False) -> Optional[str]:
    args = ["rev-parse", "--short", "HEAD"] if short else ["rev-parse", "HEAD"]
    return _run_git(args, cwd=cwd)
def get_branch(cwd: Optional[PathLike] = None) -> Optional[str]:
    # Prefer symbolic-ref (fails in detached HEAD), then fall back to HEAD name.
    out = _run_git(["symbolic-ref", "--quiet", "--short", "HEAD"], cwd=cwd)
    if out:
        return out
    out = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    if out and out != "HEAD":
        return out
    return None
def is_dirty(cwd: Optional[PathLike] = None) -> Optional[bool]:
    if not is_git_repo(cwd=cwd):
        return None
    out = _run_git(["status", "--porcelain"], cwd=cwd)
    if out is None:
        return None
    return bool(out.strip())
def get_describe(cwd: Optional[PathLike] = None) -> Optional[str]:
    # "Always" gives something even without tags; dirty suffix improves usefulness.
    out = _run_git(["describe", "--tags", "--always", "--dirty"], cwd=cwd)
    return out
def get_git_info(cwd: Optional[PathLike] = None) -> GitInfo:
    repo_root = _git_repo_root(cwd=cwd)
    if repo_root is None:
        return GitInfo(commit=None, branch=None, is_dirty=None, describe=None, repo_root=None)
    return GitInfo(
        commit=get_commit_hash(cwd=cwd, short=False),
        branch=get_branch(cwd=cwd),
        is_dirty=is_dirty(cwd=cwd),
        describe=get_describe(cwd=cwd),
        repo_root=repo_root,
    )
def git_metadata(cwd: Optional[PathLike] = None) -> Dict[str, Any]:
    gi = get_git_info(cwd=cwd)
    return {
        "git_commit": gi.commit,
        "git_branch": gi.branch,
        "git_is_dirty": gi.is_dirty,
        "git_describe": gi.describe,
        "git_repo_root": gi.repo_root,
    }
