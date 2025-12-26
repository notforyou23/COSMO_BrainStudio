from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union
import os


PathLike = Union[str, Path]


def _as_path(p: Optional[PathLike]) -> Optional[Path]:
    if p is None:
        return None
    return p if isinstance(p, Path) else Path(p)


def _default_outputs_root() -> Path:
    env = os.environ.get("PIPELINE_OUTPUT_DIR") or os.environ.get("OUTPUT_DIR")
    if env:
        return Path(env)
    return Path.cwd() / "outputs"


@dataclass(frozen=True)
class OutputPaths:
    """Canonical pipeline output layout.

    Layout:
      <outputs_root>/
        results.json
        figure.png
        metadata/   (optional)
    """

    outputs_root: Path

    @staticmethod
    def from_root(outputs_root: Optional[PathLike] = None, *, ensure: bool = True) -> "OutputPaths":
        root = _as_path(outputs_root) or _default_outputs_root()
        obj = OutputPaths(outputs_root=root)
        if ensure:
            obj.ensure_dirs()
        return obj

    @property
    def results_json(self) -> Path:
        return self.outputs_root / "results.json"

    @property
    def figure_png(self) -> Path:
        return self.outputs_root / "figure.png"

    @property
    def metadata_dir(self) -> Path:
        return self.outputs_root / "metadata"

    def metadata_path(self, name: str) -> Path:
        name = name.strip().lstrip("/").replace("\\", "/")
        if name in {"", ".", ".."} or name.endswith("/"):
            raise ValueError(f"Invalid metadata file name: {name!r}")
        p = (self.metadata_dir / name)
        if self.metadata_dir not in p.parents:
            raise ValueError(f"Metadata path escapes metadata_dir: {name!r}")
        return p

    def ensure_dirs(self) -> None:
        self.outputs_root.mkdir(parents=True, exist_ok=True)

    def ensure_metadata_dir(self) -> Path:
        self.ensure_dirs()
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        return self.metadata_dir

    def as_dict(self) -> dict:
        return {
            "outputs_root": str(self.outputs_root),
            "results_json": str(self.results_json),
            "figure_png": str(self.figure_png),
            "metadata_dir": str(self.metadata_dir),
        }


def get_output_paths(outputs_root: Optional[PathLike] = None, *, ensure: bool = True) -> OutputPaths:
    """Convenience wrapper to construct OutputPaths."""
    return OutputPaths.from_root(outputs_root=outputs_root, ensure=ensure)
