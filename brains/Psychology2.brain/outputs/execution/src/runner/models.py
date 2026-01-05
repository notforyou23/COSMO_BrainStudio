from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence
import hashlib
import json
def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False)

def stable_hash(data: Any) -> str:
    raw = _json_dumps(data).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
@dataclass(frozen=True)
class DockerMount:
    source: str
    target: str
    read_only: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {"source": self.source, "target": self.target, "read_only": self.read_only}
@dataclass
class RunnerConfig:
    image: str
    command: List[str]
    env: Dict[str, str] = field(default_factory=dict)
    workdir: Optional[str] = None
    mounts: List[DockerMount] = field(default_factory=list)
    name: Optional[str] = None
    network: Optional[str] = None
    user: Optional[str] = None
    timeout_seconds: Optional[float] = None
    capture_env: bool = True

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["mounts"] = [m.to_dict() for m in self.mounts]
        return d

    def config_hash(self) -> str:
        return stable_hash(self.to_dict())

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "RunnerConfig":
        mounts = [DockerMount(**m) for m in (d.get("mounts") or [])]
        return cls(
            image=str(d["image"]),
            command=list(d["command"]),
            env=dict(d.get("env") or {}),
            workdir=d.get("workdir"),
            mounts=mounts,
            name=d.get("name"),
            network=d.get("network"),
            user=d.get("user"),
            timeout_seconds=d.get("timeout_seconds"),
            capture_env=bool(d.get("capture_env", True)),
        )
@dataclass(frozen=True)
class RunArtifacts:
    logs_dir: str
    log_path: str
    env_snapshot_path: str
    config_path: str
    summary_path: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
@dataclass
class RunSummary:
    schema_version: int = 1
    run_id: str = ""
    status: str = ""
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_seconds: Optional[float] = None

    exit_code: Optional[int] = None
    docker_image: Optional[str] = None
    command: List[str] = field(default_factory=list)

    container_id: Optional[str] = None
    container_lost: bool = False
    container_lost_at: Optional[str] = None
    container_lost_reason: Optional[str] = None

    error_type: Optional[str] = None
    error_message: Optional[str] = None

    config_hash: Optional[str] = None
    artifacts: Optional[RunArtifacts] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = asdict(self)
        d["artifacts"] = self.artifacts.to_dict() if self.artifacts else None
        return d

    def to_json(self) -> str:
        return _json_dumps(self.to_dict()) + "\n"

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "RunSummary":
        art = d.get("artifacts")
        artifacts = RunArtifacts(**art) if isinstance(art, dict) else None
        return cls(
            schema_version=int(d.get("schema_version", 1)),
            run_id=str(d.get("run_id", "")),
            status=str(d.get("status", "")),
            started_at=d.get("started_at"),
            finished_at=d.get("finished_at"),
            duration_seconds=d.get("duration_seconds"),
            exit_code=d.get("exit_code"),
            docker_image=d.get("docker_image"),
            command=list(d.get("command") or []),
            container_id=d.get("container_id"),
            container_lost=bool(d.get("container_lost", False)),
            container_lost_at=d.get("container_lost_at"),
            container_lost_reason=d.get("container_lost_reason"),
            error_type=d.get("error_type"),
            error_message=d.get("error_message"),
            config_hash=d.get("config_hash"),
            artifacts=artifacts,
            extra=dict(d.get("extra") or {}),
        )

    @classmethod
    def from_json(cls, s: str) -> "RunSummary":
        return cls.from_dict(json.loads(s))

    def mark_container_lost(self, reason: str, when_iso: Optional[str] = None) -> None:
        self.container_lost = True
        self.container_lost_reason = reason
        self.container_lost_at = when_iso or utcnow_iso()
