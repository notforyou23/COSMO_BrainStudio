from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import datetime as _dt
import hashlib
import json
SCHEMA_VERSION = 1

@dataclass(frozen=True)
class ArtifactSpec:
    name: str
    path: str
    required: bool = True
    min_bytes: int = 1

def default_checklist() -> List[ArtifactSpec]:
    return [
        ArtifactSpec(name="run_manifest", path="artifacts/run_manifest.json", required=True, min_bytes=2),
        ArtifactSpec(name="qa_log", path="artifacts/qa.log", required=True, min_bytes=1),
        ArtifactSpec(name="artifact_checklist", path="artifacts/artifact_checklist.json", required=True, min_bytes=2),
    ]
def _utc_now_iso() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).isoformat().replace("+00:00", "Z")

def normalize_path(root: Path, p: Path) -> str:
    root = root.resolve()
    p = p.resolve()
    try:
        rel = p.relative_to(root)
        return rel.as_posix()
    except Exception:
        return p.as_posix()

def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

def sha256_file(path: Path, max_bytes: Optional[int] = None) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        remaining = max_bytes
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            if remaining is not None:
                if len(chunk) > remaining:
                    chunk = chunk[:remaining]
                remaining -= len(chunk)
            h.update(chunk)
            if remaining is not None and remaining <= 0:
                break
    return h.hexdigest()
def verify_artifacts(root: Path, specs: Iterable[ArtifactSpec]) -> List[Dict[str, Any]]:
    root = root.resolve()
    out: List[Dict[str, Any]] = []
    for spec in specs:
        p = (root / spec.path).resolve()
        exists = p.exists() and p.is_file()
        size = p.stat().st_size if exists else 0
        ok = (exists and size >= int(spec.min_bytes)) or (not spec.required and not exists)
        err = None
        if spec.required and not exists:
            err = "missing"
        elif exists and size < int(spec.min_bytes):
            err = f"too_small<{spec.min_bytes}"
        out.append(
            {
                "name": spec.name,
                "path": normalize_path(root, p),
                "required": bool(spec.required),
                "min_bytes": int(spec.min_bytes),
                "exists": bool(exists),
                "bytes": int(size),
                "ok": bool(ok),
                "error": err,
            }
        )
    out.sort(key=lambda d: (d["name"], d["path"]))
    return out
def build_run_manifest(
    root: Path,
    produced_paths: Iterable[Tuple[str, Path]],
    checklist_results: Optional[List[Dict[str, Any]]] = None,
    extra: Optional[Dict[str, Any]] = None,
    include_hash: bool = True,
) -> Dict[str, Any]:
    root = root.resolve()
    artifacts: List[Dict[str, Any]] = []
    for name, p in produced_paths:
        p = (p if p.is_absolute() else (root / p)).resolve()
        rec: Dict[str, Any] = {"name": str(name), "path": normalize_path(root, p)}
        if p.exists() and p.is_file():
            st = p.stat()
            rec["bytes"] = int(st.st_size)
            if include_hash:
                rec["sha256"] = sha256_file(p)
        artifacts.append(rec)
    artifacts.sort(key=lambda d: (d.get("name", ""), d.get("path", "")))
    manifest: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "created_utc": _utc_now_iso(),
        "root": normalize_path(root, root),
        "artifacts": artifacts,
        "checks": {"artifact_checklist": checklist_results or []},
    }
    if extra:
        manifest["extra"] = extra
    return manifest
def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

def write_json(path: Path, obj: Any) -> None:
    ensure_parent(path)
    path.write_text(_json_dumps(obj), encoding="utf-8")

def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def write_manifest(path: Path, manifest: Dict[str, Any]) -> None:
    write_json(path, manifest)

def load_manifest(path: Path) -> Dict[str, Any]:
    m = read_json(path)
    if not isinstance(m, dict):
        raise ValueError("manifest must be a JSON object")
    if int(m.get("schema_version", -1)) != SCHEMA_VERSION:
        raise ValueError(f"unsupported schema_version: {m.get('schema_version')}")
    if "artifacts" not in m or not isinstance(m["artifacts"], list):
        raise ValueError("manifest.artifacts must be a list")
    if "checks" in m and not isinstance(m["checks"], dict):
        raise ValueError("manifest.checks must be an object if present")
    return m
