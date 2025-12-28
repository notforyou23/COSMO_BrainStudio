from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

try:
    from pydantic import BaseModel, Field
except Exception:  # pragma: no cover
    BaseModel = object  # type: ignore
    Field = lambda default=None, **kwargs: default  # type: ignore


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class _Model(BaseModel):
    if hasattr(BaseModel, "model_config"):  # pydantic v2
        model_config = {"extra": "forbid", "frozen": True}
    else:  # pydantic v1
        class Config:
            extra = "forbid"
            allow_mutation = False

    def as_dict(self) -> Dict[str, Any]:
        if hasattr(self, "model_dump"):
            return self.model_dump(mode="json")  # type: ignore[attr-defined]
        return self.dict()  # type: ignore[no-any-return]

    def as_jsonable(self) -> Dict[str, Any]:
        d = self.as_dict()
        for k, v in list(d.items()):
            if isinstance(v, _Model):
                d[k] = v.as_jsonable()
        return d


class RiskThresholds(_Model):
    max_overall: float = Field(0.5, ge=0.0, le=1.0, description="Fail run if overall risk exceeds this threshold.")
    max_category: float = Field(
        0.7, ge=0.0, le=1.0, description="Fail run if any single category risk exceeds this threshold."
    )
    max_uncertainty: float = Field(
        0.8, ge=0.0, le=1.0, description="Fail run if uncertainty exceeds this threshold."
    )
    deterministic_checks: bool = Field(True, description="Enforce deterministic constraint checks.")


class ClaimDecompositionConfig(_Model):
    enabled: bool = Field(False, description="Whether to decompose claims for goal_10/goal_12 sweeps.")
    max_claims: int = Field(32, ge=1, le=1024, description="Maximum number of claims to emit when enabled.")


DecisionEventType = Literal[
    "run_start",
    "config",
    "constraint_check",
    "decision",
    "artifact_written",
    "run_end",
    "error",
]


class DecisionTraceEvent(_Model):
    ts: str = Field(default_factory=utc_now_iso, description="UTC timestamp in ISO-8601 Z format.")
    event_type: DecisionEventType
    name: str = Field(..., description="Stable, machine-readable event name.")
    message: str = Field("", description="Human-readable message.")
    level: Literal["debug", "info", "warning", "error"] = "info"
    data: Dict[str, Any] = Field(default_factory=dict, description="Structured event payload.")


class RunManifest(_Model):
    schema_version: str = Field("1", description="Schema version for this manifest.")
    run_id: str = Field(..., description="Stable run identifier used for build dir naming.")
    created_at: str = Field(default_factory=utc_now_iso)
    tool: str = Field("cli_tool")
    tool_version: Optional[str] = None

    command: List[str] = Field(default_factory=list, description="Full invoked command argv vector.")
    seed: int = Field(0, ge=0, description="Deterministic seed used for run.")
    build_dir: str = Field(..., description="Canonical build directory under runtime/_build/.")

    input_ref: Optional[str] = Field(None, description="Optional input path or identifier.")
    risk: RiskThresholds = Field(default_factory=RiskThresholds)
    claim_decomposition: ClaimDecompositionConfig = Field(default_factory=ClaimDecompositionConfig)

    def stable_identity(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "tool": self.tool,
            "tool_version": self.tool_version,
            "command": list(self.command),
            "seed": self.seed,
            "build_dir": self.build_dir,
            "input_ref": self.input_ref,
            "risk": self.risk.as_jsonable(),
            "claim_decomposition": self.claim_decomposition.as_jsonable(),
        }
