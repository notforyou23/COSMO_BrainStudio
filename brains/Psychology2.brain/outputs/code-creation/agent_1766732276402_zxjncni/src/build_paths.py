from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Union


PathLike = Union[str, Path]


def find_project_root(start: Optional[PathLike] = None) -> Path:
    """Best-effort repo root discovery for stable runtime/_build paths."""
    p = Path(start).resolve() if start is not None else Path(__file__).resolve()
    if p.is_file():
        p = p.parent
    for cur in (p, *p.parents):
        if (cur / "src").is_dir():
            return cur
    return p


def ensure_dir(path: Path, *, clean: bool = False) -> Path:
    if clean and path.exists():
        for child in sorted(path.glob("**/*"), reverse=True):
            if child.is_file() or child.is_symlink():
                child.unlink(missing_ok=True)
            elif child.is_dir():
                try:
                    child.rmdir()
                except OSError:
                    pass
    path.mkdir(parents=True, exist_ok=True)
    return path
@dataclass(frozen=True)
class BuildPaths:
    root: Path

    @classmethod
    def from_project_root(cls, project_root: Optional[PathLike] = None) -> "BuildPaths":
        return cls(root=find_project_root(project_root))

    @property
    def runtime_dir(self) -> Path:
        return self.root / "runtime"

    @property
    def build_root(self) -> Path:
        return self.runtime_dir / "_build"

    def step_dir(self, step: str) -> Path:
        return self.build_root / step

    def step_logs_dir(self, step: str) -> Path:
        return self.step_dir(step) / "logs"

    def step_artifacts_dir(self, step: str) -> Path:
        return self.step_dir(step) / "artifacts"

    def step_raw_log_path(self, step: str) -> Path:
        return self.step_logs_dir(step) / "raw.log"

    def step_summary_path(self, step: str) -> Path:
        return self.step_dir(step) / "summary.json"

    def final_summary_path(self) -> Path:
        return self.build_root / "final_summary.json"

    def ensure_layout(self, *, steps: Optional[list[str]] = None, clean: bool = False) -> Dict[str, Path]:
        """Create standardized runtime/_build layout; returns created key paths."""
        created: Dict[str, Path] = {}
        created["runtime_dir"] = ensure_dir(self.runtime_dir)
        created["build_root"] = ensure_dir(self.build_root, clean=clean)
        for name in (steps or []):
            created[f"{name}_dir"] = ensure_dir(self.step_dir(name), clean=clean)
            created[f"{name}_logs"] = ensure_dir(self.step_logs_dir(name), clean=clean)
            created[f"{name}_artifacts"] = ensure_dir(self.step_artifacts_dir(name), clean=clean)
        return created
def normalize_step_name(step: str) -> str:
    s = (step or "").strip().lower().replace(" ", "_").replace("-", "_")
    if not s:
        raise ValueError("step name must be non-empty")
    return s


def write_json(path: Path, data: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json_dumps(data) + "\n", encoding="utf-8")
    return path


def json_dumps(data: object) -> str:
    import json

    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False)


def default_build_paths(project_root: Optional[PathLike] = None) -> BuildPaths:
    return BuildPaths.from_project_root(project_root)
