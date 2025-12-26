"""Canonical artifact models and writers for /outputs.

This module defines deterministic paths and minimal metadata for:
- outputs index (outputs/index.json)
- run evidence (outputs/runs/<run_id>/run_evidence.json)
- a domain artifact stub (outputs/runs/<run_id>/domain_artifact_stub.json)
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


SCHEMA_VERSION = "1.0"
OUTPUTS_DIRNAME = "outputs"
RUNS_DIRNAME = "runs"


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json_dumps(payload) + "\n", encoding="utf-8")


def json_dumps(obj: Any) -> str:
    import json
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False)


@dataclass(frozen=True)
class ArtifactMeta:
    artifact_type: str
    path: str
    schema_version: str = SCHEMA_VERSION
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if not d["created_at"]:
            d["created_at"] = now_utc_iso()
        return d


@dataclass(frozen=True)
class ArtifactPaths:
    base_dir: Path

    @property
    def outputs_dir(self) -> Path:
        return self.base_dir / OUTPUTS_DIRNAME

    @property
    def index_path(self) -> Path:
        return self.outputs_dir / "index.json"

    def run_dir(self, run_id: str) -> Path:
        return self.outputs_dir / RUNS_DIRNAME / run_id

    def run_evidence_path(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "run_evidence.json"

    def domain_stub_path(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "domain_artifact_stub.json"
def init_outputs_index(paths: ArtifactPaths) -> Dict[str, Any]:
    if paths.index_path.exists():
        import json
        return json.loads(paths.index_path.read_text(encoding="utf-8"))
    return {"schema_version": SCHEMA_VERSION, "created_at": now_utc_iso(), "runs": {}}


def update_outputs_index(paths: ArtifactPaths, run_id: str, artifacts: List[Dict[str, Any]]) -> None:
    idx = init_outputs_index(paths)
    idx.setdefault("runs", {})
    idx["runs"][run_id] = {
        "run_id": run_id,
        "updated_at": now_utc_iso(),
        "artifacts": sorted(artifacts, key=lambda a: (a.get("artifact_type", ""), a.get("path", ""))),
    }
    _write_json(paths.index_path, idx)


def write_run_evidence(
    paths: ArtifactPaths,
    run_id: str,
    status: str,
    details: Optional[Dict[str, Any]] = None,
    artifacts: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "meta": ArtifactMeta("run_evidence", str(paths.run_evidence_path(run_id).relative_to(paths.base_dir))).to_dict(),
        "run_id": run_id,
        "status": status,
        "recorded_at": now_utc_iso(),
        "details": details or {},
        "artifacts": artifacts or [],
    }
    _write_json(paths.run_evidence_path(run_id), payload)
    return payload


def write_domain_artifact_stub(
    paths: ArtifactPaths,
    run_id: str,
    name: str = "survey_results_stub",
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    body = {
        "meta": ArtifactMeta("domain_artifact_stub", str(paths.domain_stub_path(run_id).relative_to(paths.base_dir))).to_dict(),
        "run_id": run_id,
        "name": name,
        "payload": payload or {"note": "Domain artifact stub created by pipeline."},
    }
    _write_json(paths.domain_stub_path(run_id), body)
    return body


def artifact_entry(meta: ArtifactMeta, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    d = {"meta": meta.to_dict()}
    if extra:
        d.update(extra)
    return {"artifact_type": d["meta"]["artifact_type"], "path": d["meta"]["path"], "meta": d["meta"], **({k: v for k, v in d.items() if k != "meta"})}
