from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence


def _is_subpath(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


def find_project_root(start: Optional[Path] = None, markers: Sequence[str] = ("pyproject.toml", ".git", "src")) -> Path:
    start = (start or Path.cwd()).resolve()
    for p in (start,) + tuple(start.parents):
        if any((p / m).exists() for m in markers):
            return p
    return start


def normalize_path(p: Path) -> Path:
    try:
        return p.expanduser().resolve()
    except Exception:
        return p.expanduser().absolute()


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_parent(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def safe_relative(path: Path, root: Path) -> str:
    path_r = normalize_path(path)
    root_r = normalize_path(root)
    try:
        return str(path_r.relative_to(root_r))
    except Exception:
        return str(path_r)


@dataclass(frozen=True)
class QAPaths:
    root: Path
    outputs: Path
    qa: Path

    @classmethod
    def from_start(cls, start: Optional[Path] = None, outputs_dirname: str = "outputs", qa_subdir: str = "qa") -> "QAPaths":
        root = find_project_root(start)
        outputs = root / outputs_dirname
        qa = outputs / qa_subdir
        return cls(root=normalize_path(root), outputs=normalize_path(outputs), qa=normalize_path(qa))

    def ensure(self) -> "QAPaths":
        ensure_dir(self.outputs)
        ensure_dir(self.qa)
        return self

    def in_outputs(self, *parts: str) -> Path:
        p = normalize_path(self.outputs.joinpath(*parts))
        if not _is_subpath(p, self.outputs):
            raise ValueError(f"Refusing to create path outside outputs/: {p}")
        return p

    def in_qa(self, *parts: str) -> Path:
        p = normalize_path(self.qa.joinpath(*parts))
        if not _is_subpath(p, self.qa):
            raise ValueError(f"Refusing to create path outside outputs/qa/: {p}")
        return p


def default_paths(start: Optional[Path] = None) -> QAPaths:
    return QAPaths.from_start(start).ensure()


def iter_existing(paths: Iterable[Path]) -> list[Path]:
    return [p for p in paths if p.exists()]
