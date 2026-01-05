from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, IO, Iterable, Mapping, Optional
import json
import os


SCHEMA_VERSION = 1
DEFAULT_BUILD_SUBDIR = Path("runtime") / "_build"


def resolve_build_root(repo_root: Path) -> Path:
    return (repo_root / DEFAULT_BUILD_SUBDIR).resolve()


def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def _atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    ensure_dir(path.parent)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding=encoding)
    os.replace(tmp, path)


def write_json(path: Path, obj: Any, *, indent: int = 2) -> None:
    text = json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=indent) + "\n"
    _atomic_write_text(path, text)


def _compact_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


@dataclass(frozen=True)
class ArtifactPaths:
    build_dir: Path
    manifest_path: Path
    logs_path: Path
    decisions_path: Path

    @staticmethod
    def for_build_dir(build_dir: Path) -> "ArtifactPaths":
        build_dir = build_dir.resolve()
        return ArtifactPaths(
            build_dir=build_dir,
            manifest_path=build_dir / "run_manifest.json",
            logs_path=build_dir / "logs.jsonl",
            decisions_path=build_dir / "decision_traces.jsonl",
        )
class JsonlWriter:
    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        ensure_dir(self.path.parent)
        self._fh: IO[str] = open(self.path, "a", encoding="utf-8", newline="\n")

    def write(self, record: Mapping[str, Any]) -> None:
        self._fh.write(_compact_json(dict(record)) + "\n")
        self._fh.flush()

    def write_many(self, records: Iterable[Mapping[str, Any]]) -> None:
        for r in records:
            self.write(r)

    def close(self) -> None:
        try:
            self._fh.flush()
        finally:
            self._fh.close()

    def __enter__(self) -> "JsonlWriter":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
def write_run_manifest(
    path: Path,
    *,
    run_id: str,
    config_hash: str,
    created_at: Optional[str] = None,
    params: Optional[Mapping[str, Any]] = None,
    environment: Optional[Mapping[str, Any]] = None,
    build_dir: Optional[str] = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    manifest: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "config_hash": config_hash,
        "created_at": created_at,
        "build_dir": build_dir,
        "params": dict(params or {}),
        "environment": dict(environment or {}),
    }
    if extra:
        manifest["extra"] = dict(extra)
    write_json(path, manifest)
    return manifest


def log_record(*, level: str, message: str, t: Optional[str] = None, **data: Any) -> Dict[str, Any]:
    rec: Dict[str, Any] = {"schema_version": SCHEMA_VERSION, "level": level, "message": message}
    if t is not None:
        rec["t"] = t
    if data:
        rec["data"] = data
    return rec


def decision_record(
    *,
    step: str,
    decision: str,
    rationale: str,
    t: Optional[str] = None,
    risk: Optional[float] = None,
    inputs: Optional[Mapping[str, Any]] = None,
    outputs: Optional[Mapping[str, Any]] = None,
    meta: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    rec: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "step": step,
        "decision": decision,
        "rationale": rationale,
    }
    if t is not None:
        rec["t"] = t
    if risk is not None:
        rec["risk"] = float(risk)
    if inputs is not None:
        rec["inputs"] = dict(inputs)
    if outputs is not None:
        rec["outputs"] = dict(outputs)
    if meta is not None:
        rec["meta"] = dict(meta)
    return rec
