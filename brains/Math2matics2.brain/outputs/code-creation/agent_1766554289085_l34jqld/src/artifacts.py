from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import os
import tempfile
from typing import Any, Dict, Mapping, Optional

def project_root() -> Path:
    return Path(__file__).resolve().parents[1]

def outputs_dir(root: Optional[Path] = None) -> Path:
    return (root or project_root()) / "outputs"

@dataclass(frozen=True)
class ArtifactPaths:
    results_json: Path
    figure_png: Path
    hashes_json: Path

    @staticmethod
    def from_root(root: Optional[Path] = None) -> "ArtifactPaths":
        out = outputs_dir(root)
        return ArtifactPaths(
            results_json=out / "results.json",
            figure_png=out / "figure.png",
            hashes_json=out / "hashes.json",
        )

    def ensure_dirs(self) -> None:
        for p in (self.results_json, self.figure_png, self.hashes_json):
            p.parent.mkdir(parents=True, exist_ok=True)

def canonical_json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)

def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass

def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    atomic_write_bytes(path, text.encode(encoding))

def sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()

def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()

def build_results_json(
    *,
    run_id: str,
    seed: int,
    metrics: Mapping[str, float],
    series: Mapping[str, Any],
    meta: Optional[Mapping[str, Any]] = None,
    schema_version: int = 1,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "schema_version": int(schema_version),
        "run_id": str(run_id),
        "seed": int(seed),
        "metrics": dict(metrics),
        "series": dict(series),
        "meta": dict(meta or {}),
    }
    _validate_results_payload(payload)
    return payload

def _validate_results_payload(payload: Mapping[str, Any]) -> None:
    required = ("schema_version", "run_id", "seed", "metrics", "series", "meta")
    for k in required:
        if k not in payload:
            raise ValueError(f"results.json missing key: {k}")
    if not isinstance(payload["schema_version"], int):
        raise TypeError("schema_version must be int")
    if not isinstance(payload["run_id"], str):
        raise TypeError("run_id must be str")
    if not isinstance(payload["seed"], int):
        raise TypeError("seed must be int")
    for k in ("metrics", "series", "meta"):
        if not isinstance(payload[k], dict):
            raise TypeError(f"{k} must be object/dict")

def write_results_json(path: Path, payload: Mapping[str, Any]) -> None:
    _validate_results_payload(payload)
    atomic_write_text(path, canonical_json_dumps(dict(payload)) + "\n")

def write_png(path: Path, png_bytes: bytes) -> None:
    if not (isinstance(png_bytes, (bytes, bytearray)) and png_bytes[:8] == b"\x89PNG\r\n\x1a\n"):
        raise ValueError("figure artifact must be PNG bytes")
    atomic_write_bytes(path, bytes(png_bytes))

def compute_hashes(paths: ArtifactPaths) -> Dict[str, str]:
    return {
        "results.json": sha256_file(paths.results_json),
        "figure.png": sha256_file(paths.figure_png),
        "hashes.json": "",  # filled after writing hashes.json
    }

def write_hashes_json(path: Path, hashes: Mapping[str, str]) -> None:
    atomic_write_text(path, canonical_json_dumps(dict(hashes)) + "\n")

def write_all_hashes(paths: ArtifactPaths) -> Dict[str, str]:
    paths.ensure_dirs()
    hashes = compute_hashes(paths)
    hashes["hashes.json"] = ""
    write_hashes_json(paths.hashes_json, hashes)
    hashes["hashes.json"] = sha256_file(paths.hashes_json)
    write_hashes_json(paths.hashes_json, hashes)
    return hashes
