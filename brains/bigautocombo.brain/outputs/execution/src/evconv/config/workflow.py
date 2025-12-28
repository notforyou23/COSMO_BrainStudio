"""Workflow configuration model and utilities.

Defines reusable workflow building blocks:
- Architecture: named system layout (cooling/thermal/etc.)
- Stage: ordered step with parameters
- WorkflowConfig: end-to-end run configuration, optionally derived from presets

This module is intentionally self-contained to reduce coupling across config layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


JsonDict = Dict[str, Any]
def _deep_update(base: Mapping[str, Any], patch: Mapping[str, Any]) -> JsonDict:
    out: JsonDict = dict(base)
    for k, v in patch.items():
        if isinstance(v, Mapping) and isinstance(out.get(k), Mapping):
            out[k] = _deep_update(out[k], v)  # type: ignore[arg-type]
        else:
            out[k] = v
    return out


def _require_nonempty(name: str, value: Optional[str]) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()
@dataclass(frozen=True)
class Architecture:
    name: str
    description: str = ""
    defaults: JsonDict = field(default_factory=dict)

    def validate(self) -> None:
        _require_nonempty("architecture.name", self.name)

    def to_dict(self) -> JsonDict:
        return {"name": self.name, "description": self.description, "defaults": dict(self.defaults)}
@dataclass(frozen=True)
class Stage:
    name: str
    kind: str
    params: JsonDict = field(default_factory=dict)
    enabled: bool = True

    def validate(self) -> None:
        _require_nonempty("stage.name", self.name)
        _require_nonempty("stage.kind", self.kind)
        if not isinstance(self.params, dict):
            raise TypeError("stage.params must be a dict")

    def to_dict(self) -> JsonDict:
        return {"name": self.name, "kind": self.kind, "params": dict(self.params), "enabled": bool(self.enabled)}
@dataclass(frozen=True)
class WorkflowConfig:
    architecture: Architecture
    stages: Tuple[Stage, ...]
    run: JsonDict = field(default_factory=dict)  # cross-cutting options (paths, seeds, caching, etc.)
    metadata: JsonDict = field(default_factory=dict)

    def validate(self) -> None:
        self.architecture.validate()
        if not self.stages:
            raise ValueError("workflow.stages cannot be empty")
        seen = set()
        for s in self.stages:
            s.validate()
            if s.name in seen:
                raise ValueError(f"duplicate stage name: {s.name}")
            seen.add(s.name)
        if not isinstance(self.run, dict) or not isinstance(self.metadata, dict):
            raise TypeError("workflow.run and workflow.metadata must be dicts")

    def to_dict(self) -> JsonDict:
        return {
            "architecture": self.architecture.to_dict(),
            "stages": [s.to_dict() for s in self.stages],
            "run": dict(self.run),
            "metadata": dict(self.metadata),
        }

    def with_overrides(self, overrides: Mapping[str, Any]) -> WorkflowConfig:
        data = self.to_dict()
        merged = _deep_update(data, overrides)
        return workflow_from_dict(merged)
def workflow_from_dict(data: Mapping[str, Any]) -> WorkflowConfig:
    arch_d = data.get("architecture") or {}
    arch = Architecture(
        name=str(arch_d.get("name") or ""),
        description=str(arch_d.get("description") or ""),
        defaults=dict(arch_d.get("defaults") or {}),
    )
    stages_d = data.get("stages") or []
    if not isinstance(stages_d, Sequence):
        raise TypeError("stages must be a list")
    stages: List[Stage] = []
    for sd in stages_d:
        if not isinstance(sd, Mapping):
            raise TypeError("each stage must be a mapping")
        stages.append(
            Stage(
                name=str(sd.get("name") or ""),
                kind=str(sd.get("kind") or ""),
                params=dict(sd.get("params") or {}),
                enabled=bool(sd.get("enabled", True)),
            )
        )
    wf = WorkflowConfig(
        architecture=arch,
        stages=tuple(stages),
        run=dict(data.get("run") or {}),
        metadata=dict(data.get("metadata") or {}),
    )
    wf.validate()
    return wf
# Convention-driven, minimal built-ins. Projects may extend by calling register_*.
ARCHITECTURES: Dict[str, Architecture] = {
    "single_phase": Architecture(
        name="single_phase",
        description="Single-phase cooling baseline architecture.",
        defaults={"coolant": {"phase": "single"}, "solver": {"mode": "steady"}},
    ),
    "two_phase": Architecture(
        name="two_phase",
        description="Two-phase cooling architecture with quality/boiling parameters.",
        defaults={"coolant": {"phase": "two"}, "solver": {"mode": "steady"}},
    ),
}

PRESETS: Dict[str, JsonDict] = {
    "default": {
        "architecture": {"name": "single_phase"},
        "stages": [
            {"name": "ingest", "kind": "io.ingest", "params": {}},
            {"name": "simulate", "kind": "model.simulate", "params": {}},
            {"name": "report", "kind": "plot.report", "params": {}},
        ],
        "run": {"strict": True},
        "metadata": {"preset": "default"},
    }
}
def register_architecture(arch: Architecture, *, overwrite: bool = False) -> None:
    arch.validate()
    if not overwrite and arch.name in ARCHITECTURES:
        raise KeyError(f"architecture already registered: {arch.name}")
    ARCHITECTURES[arch.name] = arch


def register_preset(name: str, preset: Mapping[str, Any], *, overwrite: bool = False) -> None:
    name = _require_nonempty("preset.name", name)
    if not overwrite and name in PRESETS:
        raise KeyError(f"preset already registered: {name}")
    PRESETS[name] = dict(preset)
def get_architecture(name: str) -> Architecture:
    name = _require_nonempty("architecture.name", name)
    try:
        return ARCHITECTURES[name]
    except KeyError as e:
        raise KeyError(f"unknown architecture: {name}") from e


def build_workflow(
    *,
    preset: str = "default",
    overrides: Optional[Mapping[str, Any]] = None,
    strict: Optional[bool] = None,
) -> WorkflowConfig:
    preset = _require_nonempty("preset", preset)
    try:
        base = PRESETS[preset]
    except KeyError as e:
        raise KeyError(f"unknown preset: {preset}") from e

    merged = dict(base)
    merged["metadata"] = _deep_update(base.get("metadata") or {}, {"preset": preset})
    if overrides:
        merged = _deep_update(merged, overrides)

    wf = workflow_from_dict(merged)
    arch_name = wf.architecture.name
    arch = get_architecture(arch_name)
    # Merge architecture defaults into run options (lowest precedence), then re-apply overrides.
    run = _deep_update(arch.defaults, wf.run)
    if strict is not None:
        run["strict"] = bool(strict)
    wf2 = WorkflowConfig(architecture=arch, stages=wf.stages, run=run, metadata=wf.metadata)
    wf2.validate()
    return wf2


def iter_enabled_stages(wf: WorkflowConfig) -> Iterable[Stage]:
    wf.validate()
    return (s for s in wf.stages if s.enabled)
