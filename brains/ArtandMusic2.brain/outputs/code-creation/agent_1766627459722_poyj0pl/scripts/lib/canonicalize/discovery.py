from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Optional, Sequence, Tuple, List, Dict
import fnmatch
import os
DEFAULT_IGNORE_DIRNAMES = {
    ".git", ".hg", ".svn",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".venv", "venv", "env",
    "node_modules", "dist", "build",
}
DEFAULT_IGNORE_GLOBS = {"*.pyc", "*.pyo", "*.DS_Store", "Thumbs.db"}

QA_RUNNER_NAMES = {
    "qa_run.py", "qa_runner.py", "run_qa.py", "qa.py",
    "qa_run.sh",
    "validate_outputs.py", "run_validation.py",
}
SCHEMA_NAME_HINTS = {
    "schema.json", "output_schema.json", "outputs_schema.json",
}
SCHEMA_GLOBS = {
    "*.schema.json", "*schema*.json", "schema*.json",
}
@dataclass(frozen=True)
class Discovered:
    qa_runners: Tuple[Path, ...] = ()
    schemas: Tuple[Path, ...] = ()
    artifacts: Tuple[Path, ...] = ()

    def as_dict(self) -> Dict[str, List[str]]:
        return {
            "qa_runners": [p.as_posix() for p in self.qa_runners],
            "schemas": [p.as_posix() for p in self.schemas],
            "artifacts": [p.as_posix() for p in self.artifacts],
        }
def _norm_roots(roots: Iterable[Path]) -> Tuple[Path, ...]:
    out: List[Path] = []
    seen: set[str] = set()
    for r in roots:
        rr = Path(r).expanduser()
        try:
            rr = rr.resolve()
        except Exception:
            rr = rr.absolute()
        key = rr.as_posix()
        if key not in seen:
            seen.add(key)
            out.append(rr)
    return tuple(sorted(out, key=lambda p: p.as_posix().lower()))


def _is_ignored_dirname(name: str, ignore_dirnames: set[str]) -> bool:
    return name in ignore_dirnames or name.startswith(".") and name not in {".", ".."}


def _matches_any_glob(name: str, globs: set[str]) -> bool:
    return any(fnmatch.fnmatch(name, pat) for pat in globs)
def iter_files(
    root: Path,
    *,
    ignore_dirnames: Optional[set[str]] = None,
    ignore_globs: Optional[set[str]] = None,
    max_depth: Optional[int] = None,
) -> Iterator[Path]:
    root = Path(root)
    if not root.exists():
        return
    ignore_dirnames = set(DEFAULT_IGNORE_DIRNAMES if ignore_dirnames is None else ignore_dirnames)
    ignore_globs = set(DEFAULT_IGNORE_GLOBS if ignore_globs is None else ignore_globs)

    root_str = root.as_posix()
    for dirpath, dirnames, filenames in os.walk(root_str, topdown=True, followlinks=False):
        dpath = Path(dirpath)
        rel = dpath.relative_to(root)
        if max_depth is not None and len(rel.parts) > max_depth:
            dirnames[:] = []
            continue

        dirnames[:] = sorted(
            [d for d in dirnames if not _is_ignored_dirname(d, ignore_dirnames)],
            key=str.lower,
        )
        filenames = sorted(filenames, key=str.lower)

        for fn in filenames:
            if _matches_any_glob(fn, ignore_globs):
                continue
            yield dpath / fn
def _is_probable_qa_runner(p: Path) -> bool:
    name = p.name
    if name in QA_RUNNER_NAMES:
        return True
    if name.endswith(".sh") and "qa" in name.lower():
        return True
    if name.endswith(".py") and ("qa" in name.lower() or "validate_outputs" in name.lower()):
        return True
    return False


def _is_probable_schema(p: Path) -> bool:
    name = p.name
    if name in SCHEMA_NAME_HINTS:
        return True
    low = name.lower()
    if low.endswith(".json"):
        if any(fnmatch.fnmatch(name, pat) for pat in SCHEMA_GLOBS):
            return True
        if "schema" in low and ("output" in low or "artifact" in low or "outputs" in low):
            return True
    return False


def _is_output_artifact(p: Path) -> bool:
    low = p.name.lower()
    if low == "artifact_index.md":
        return True
    if p.suffix.lower() in {".md", ".json", ".csv", ".tsv", ".txt", ".html"}:
        parts = [x.lower() for x in p.parts]
        if "outputs" in parts or ("runtime" in parts and "outputs" in parts):
            return True
    return False
def discover(
    roots: Sequence[Path],
    *,
    ignore_dirnames: Optional[set[str]] = None,
    ignore_globs: Optional[set[str]] = None,
    max_depth: Optional[int] = None,
) -> Discovered:
    roots_n = _norm_roots(roots)
    qa: List[Path] = []
    schemas: List[Path] = []
    artifacts: List[Path] = []

    seen: set[str] = set()
    def add(lst: List[Path], p: Path) -> None:
        try:
            rp = p.resolve()
        except Exception:
            rp = p.absolute()
        k = rp.as_posix()
        if k not in seen:
            seen.add(k)
            lst.append(rp)

    for r in roots_n:
        for p in iter_files(r, ignore_dirnames=ignore_dirnames, ignore_globs=ignore_globs, max_depth=max_depth):
            if _is_probable_qa_runner(p):
                add(qa, p)
            if _is_probable_schema(p):
                add(schemas, p)
            if _is_output_artifact(p):
                add(artifacts, p)

    key = lambda p: p.as_posix().lower()
    return Discovered(
        qa_runners=tuple(sorted(qa, key=key)),
        schemas=tuple(sorted(schemas, key=key)),
        artifacts=tuple(sorted(artifacts, key=key)),
    )
def discover_from_default_locations(project_root: Path) -> Discovered:
    pr = Path(project_root)
    candidates = [pr]
    for d in ("runtime", "outputs", "agents", "runs"):
        p = pr / d
        if p.exists():
            candidates.append(p)
    return discover(candidates)
