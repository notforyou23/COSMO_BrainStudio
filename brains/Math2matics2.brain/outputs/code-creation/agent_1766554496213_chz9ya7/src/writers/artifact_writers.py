from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Union
import json
import os
import shutil

try:
    from src.utils.output_paths import OUTPUT_DIR, output_path  # type: ignore
except Exception:  # pragma: no cover
    OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./outputs")).resolve()

    def output_path(*parts: Union[str, Path], mkdir: bool = False) -> Path:
        p = OUTPUT_DIR
        for part in parts:
            p = p / str(part)
        if mkdir:
            p.parent.mkdir(parents=True, exist_ok=True)
        return p


def _ensure_parent(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _as_rel_path(path: Union[str, Path]) -> Path:
    p = Path(path)
    if p.is_absolute():
        raise ValueError(f"Artifact path must be relative to OUTPUT_DIR, got: {p}")
    return p


@dataclass(frozen=True)
class ArtifactWriteResult:
    path: Path


class ArtifactWriter:
    def write(self, artifact: Any, relative_path: Union[str, Path], **kwargs: Any) -> ArtifactWriteResult:
        raise NotImplementedError


class TextArtifactWriter(ArtifactWriter):
    def write(
        self,
        artifact: str,
        relative_path: Union[str, Path],
        *,
        encoding: str = "utf-8",
        newline: Optional[str] = "\n",
    ) -> ArtifactWriteResult:
        rel = _as_rel_path(relative_path)
        out = _ensure_parent(output_path(rel, mkdir=True))
        out.write_text(artifact, encoding=encoding, newline=newline)
        return ArtifactWriteResult(path=out)


class JSONArtifactWriter(ArtifactWriter):
    def write(
        self,
        artifact: Any,
        relative_path: Union[str, Path],
        *,
        indent: int = 2,
        sort_keys: bool = True,
        ensure_ascii: bool = False,
    ) -> ArtifactWriteResult:
        rel = _as_rel_path(relative_path)
        out = _ensure_parent(output_path(rel, mkdir=True))
        out.write_text(
            json.dumps(artifact, indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii) + "\n",
            encoding="utf-8",
        )
        return ArtifactWriteResult(path=out)


class BytesArtifactWriter(ArtifactWriter):
    def write(self, artifact: bytes, relative_path: Union[str, Path]) -> ArtifactWriteResult:
        rel = _as_rel_path(relative_path)
        out = _ensure_parent(output_path(rel, mkdir=True))
        out.write_bytes(artifact)
        return ArtifactWriteResult(path=out)


class CopyFileArtifactWriter(ArtifactWriter):
    def write(
        self,
        artifact: Union[str, Path],
        relative_path: Union[str, Path],
        *,
        overwrite: bool = True,
    ) -> ArtifactWriteResult:
        src = Path(artifact)
        if not src.exists():
            raise FileNotFoundError(str(src))
        rel = _as_rel_path(relative_path)
        dst = _ensure_parent(output_path(rel, mkdir=True))
        if dst.exists():
            if not overwrite:
                raise FileExistsError(str(dst))
            if dst.is_dir():
                shutil.rmtree(dst)
            else:
                dst.unlink()
        shutil.copy2(src, dst)
        return ArtifactWriteResult(path=dst)


def write_artifact(
    artifact: Any,
    relative_path: Union[str, Path],
    *,
    kind: str = "auto",
    **kwargs: Any,
) -> ArtifactWriteResult:
    rel = _as_rel_path(relative_path)
    suffix = rel.suffix.lower()
    if kind == "auto":
        if suffix in {".json"}:
            return JSONArtifactWriter().write(artifact, rel, **kwargs)
        if isinstance(artifact, (bytes, bytearray)) or suffix in {".bin"}:
            data = bytes(artifact) if isinstance(artifact, bytearray) else artifact
            return BytesArtifactWriter().write(data, rel, **kwargs)
        if isinstance(artifact, (str, int, float, bool)) or suffix in {".txt", ".md", ".log", ".csv"}:
            return TextArtifactWriter().write(str(artifact), rel, **kwargs)
        return JSONArtifactWriter().write(artifact, rel, **kwargs)
    if kind == "text":
        return TextArtifactWriter().write(str(artifact), rel, **kwargs)
    if kind == "json":
        return JSONArtifactWriter().write(artifact, rel, **kwargs)
    if kind == "bytes":
        return BytesArtifactWriter().write(bytes(artifact), rel, **kwargs)
    if kind == "copy":
        return CopyFileArtifactWriter().write(artifact, rel, **kwargs)
    raise ValueError(f"Unknown kind: {kind}")
