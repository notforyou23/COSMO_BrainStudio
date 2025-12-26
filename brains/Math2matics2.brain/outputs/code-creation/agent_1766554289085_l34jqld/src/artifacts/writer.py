from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _utc_iso(ts: Optional[datetime] = None) -> str:
    dt = ts or datetime.now(timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _run_git(args: List[str], cwd: Path) -> Optional[str]:
    try:
        p = subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            text=True,
        )
        out = (p.stdout or "").strip()
        return out if p.returncode == 0 and out else None
    except Exception:
        return None


def get_git_info(cwd: Path) -> Dict[str, Any]:
    commit = _run_git(["rev-parse", "HEAD"], cwd)
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
    dirty = False
    s = _run_git(["status", "--porcelain"], cwd)
    if s is not None:
        dirty = bool(s.strip())
    return {"commit": commit, "branch": branch, "is_dirty": dirty}


_slug_re = re.compile(r"[^a-zA-Z0-9]+")


def slugify(s: str) -> str:
    s = (s or "").strip()
    s = _slug_re.sub("_", s).strip("_").lower()
    return s or "artifact"


def _validate_results_schema(obj: Dict[str, Any]) -> None:
    if not isinstance(obj, dict):
        raise TypeError("results.json root must be an object")
    for k in ("schema_version", "metadata", "results", "artifacts"):
        if k not in obj:
            raise ValueError(f"missing key: {k}")
    if not isinstance(obj["schema_version"], str):
        raise TypeError("schema_version must be str")
    md = obj["metadata"]
    if not isinstance(md, dict):
        raise TypeError("metadata must be object")
    for k in ("created_at", "run_started_at", "run_ended_at", "seed", "git"):
        if k not in md:
            raise ValueError(f"metadata missing key: {k}")
    if not (md["seed"] is None or isinstance(md["seed"], int)):
        raise TypeError("metadata.seed must be int or null")
    git = md["git"]
    if not isinstance(git, dict):
        raise TypeError("metadata.git must be object")
    for k in ("commit", "branch", "is_dirty"):
        if k not in git:
            raise ValueError(f"metadata.git missing key: {k}")
    if not isinstance(obj["results"], dict):
        raise TypeError("results must be object")
    arts = obj["artifacts"]
    if not isinstance(arts, dict):
        raise TypeError("artifacts must be object")
    for k in ("figures", "files"):
        if k not in arts:
            raise ValueError(f"artifacts missing key: {k}")
        if not isinstance(arts[k], list):
            raise TypeError(f"artifacts.{k} must be list")


@dataclass
class ArtifactRef:
    path: str
    kind: str
    caption: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"path": self.path, "kind": self.kind}
        if self.caption:
            d["caption"] = self.caption
        return d


class ArtifactWriter:
    SCHEMA_VERSION = "artifacts.results.v1"

    def __init__(
        self,
        run_dir: Path | str,
        *,
        seed: Optional[int] = None,
        repo_root: Optional[Path | str] = None,
        run_started_at: Optional[str] = None,
    ) -> None:
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.seed = seed
        self.repo_root = Path(repo_root) if repo_root else self._infer_repo_root()
        self.run_started_at = run_started_at or _utc_iso()
        self.created_at = _utc_iso()
        self._figures: List[ArtifactRef] = []
        self._files: List[ArtifactRef] = []

    def _infer_repo_root(self) -> Path:
        p = self.run_dir
        for _ in range(12):
            if (p / ".git").exists():
                return p
            if p.parent == p:
                break
            p = p.parent
        return self.run_dir

    def deterministic_name(self, kind: str, stem: str, *, idx: Optional[int] = None, ext: str = "") -> str:
        k = slugify(kind)
        s = slugify(stem)
        n = f"{k}_{s}"
        if idx is not None:
            n += f"_{int(idx):03d}"
        if ext:
            ext = ext if ext.startswith(".") else f".{ext}"
            n += ext
        return n

    def figure_path(self, stem: str, *, idx: Optional[int] = None, ext: str = "png") -> Path:
        return self.run_dir / self.deterministic_name("fig", stem, idx=idx, ext=ext)

    def file_path(self, stem: str, *, idx: Optional[int] = None, ext: str = "") -> Path:
        return self.run_dir / self.deterministic_name("file", stem, idx=idx, ext=ext)

    def register_figure(self, path: Path | str, *, caption: Optional[str] = None) -> None:
        p = str(Path(path).resolve())
        rel = str(Path(p).relative_to(self.run_dir.resolve())) if p.startswith(str(self.run_dir.resolve())) else p
        self._figures.append(ArtifactRef(path=rel, kind="figure", caption=caption))

    def register_file(self, path: Path | str, *, caption: Optional[str] = None) -> None:
        p = str(Path(path).resolve())
        rel = str(Path(p).relative_to(self.run_dir.resolve())) if p.startswith(str(self.run_dir.resolve())) else p
        self._files.append(ArtifactRef(path=rel, kind="file", caption=caption))

    def write_results(
        self,
        results: Dict[str, Any],
        *,
        extra_metadata: Optional[Dict[str, Any]] = None,
        run_ended_at: Optional[str] = None,
        filename: str = "results.json",
    ) -> Path:
        run_ended_at = run_ended_at or _utc_iso()
        md: Dict[str, Any] = {
            "created_at": self.created_at,
            "run_started_at": self.run_started_at,
            "run_ended_at": run_ended_at,
            "seed": self.seed,
            "git": get_git_info(self.repo_root),
            "cwd": os.getcwd(),
        }
        if extra_metadata:
            for k, v in extra_metadata.items():
                if k not in md:
                    md[k] = v
        figs = sorted((r.as_dict() for r in self._figures), key=lambda d: d["path"])
        files = sorted((r.as_dict() for r in self._files), key=lambda d: d["path"])
        obj: Dict[str, Any] = {
            "schema_version": self.SCHEMA_VERSION,
            "metadata": md,
            "results": results or {},
            "artifacts": {"figures": figs, "files": files},
        }
        _validate_results_schema(obj)
        out = self.run_dir / filename
        out.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return out
