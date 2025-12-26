"""Benchmark contract schema + JSON loader/validator."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Union

from .compare import CompareSpec


@dataclass(frozen=True)
class ToleranceSpec:
    """Numeric comparison policy; per_field keys use compare() paths (e.g. $.x[0])."""
    atol: float = 0.0
    rtol: float = 0.0
    nan_equal: bool = True
    inf_equal: bool = True
    per_field: Dict[str, "ToleranceSpec"] = field(default_factory=dict)

    def to_compare_spec(self) -> CompareSpec:
        return CompareSpec(self.atol, self.rtol, self.nan_equal, self.inf_equal,
                           {k: v.to_compare_spec() for k, v in self.per_field.items()})

    @staticmethod
    def from_dict(d: Mapping[str, Any]) -> "ToleranceSpec":
        if not isinstance(d, Mapping):
            raise TypeError("tolerance must be a mapping")
        per = d.get("per_field") or {}
        if not isinstance(per, Mapping):
            raise TypeError("tolerance.per_field must be a mapping")
        return ToleranceSpec(float(d.get("atol", 0.0)), float(d.get("rtol", 0.0)),
                             bool(d.get("nan_equal", True)), bool(d.get("inf_equal", True)),
                             {str(k): ToleranceSpec.from_dict(v) for k, v in per.items()})

    def validate(self, ctx: str) -> None:
        if self.atol < 0 or self.rtol < 0:
            raise ValueError(f"{ctx}: atol/rtol must be >= 0 (got atol={self.atol} rtol={self.rtol})")
        for k, v in self.per_field.items():
            if not k:
                raise ValueError(f"{ctx}.per_field: keys must be non-empty strings")
            v.validate(f"{ctx}.per_field[{k!r}]")
@dataclass(frozen=True)
class ObservableContract:
    description: str
    tolerance: ToleranceSpec
    tolerance_notes: str

    @staticmethod
    def from_dict(d: Mapping[str, Any]) -> "ObservableContract":
        if not isinstance(d, Mapping):
            raise TypeError("observable spec must be a mapping")
        if d.get("tolerance") is None:
            raise ValueError("observable is missing required field 'tolerance'")
        return ObservableContract(
            description=str(d.get("description", "")).strip(),
            tolerance=ToleranceSpec.from_dict(d["tolerance"]),
            tolerance_notes=str(d.get("tolerance_notes", "")).strip(),
        )

    def validate(self, name: str) -> None:
        if not self.tolerance_notes:
            raise ValueError(f"observable '{name}' must set non-empty 'tolerance_notes'")
        self.tolerance.validate(f"observables[{name}].tolerance")
@dataclass(frozen=True)
class BenchmarkContract:
    task_id: str
    version: str
    description: str
    reference: Dict[str, Any]
    observables: Dict[str, ObservableContract]

    @staticmethod
    def from_dict(d: Mapping[str, Any]) -> "BenchmarkContract":
        if not isinstance(d, Mapping):
            raise TypeError("contract must be a mapping")
        obs = d.get("observables")
        if not isinstance(obs, Mapping) or not obs:
            raise ValueError("contract must define non-empty 'observables' mapping")
        return BenchmarkContract(
            task_id=str(d.get("task_id", "")).strip(),
            version=str(d.get("version", "")).strip(),
            description=str(d.get("description", "")).strip(),
            reference=dict(d.get("reference", {}) or {}),
            observables={str(k): ObservableContract.from_dict(v) for k, v in obs.items()},
        )

    def validate(self) -> None:
        if not self.task_id:
            raise ValueError("contract missing required field 'task_id'")
        if not self.version:
            raise ValueError("contract missing required field 'version'")
        if not self.description:
            raise ValueError("contract missing required field 'description'")
        if not isinstance(self.reference, dict) or not self.reference:
            raise ValueError("contract missing required non-empty field 'reference'")
        for name, oc in self.observables.items():
            if not name:
                raise ValueError("observable name must be non-empty")
            oc.validate(name)

    def compare_spec_for(self, observable: str) -> CompareSpec:
        return self.observables[observable].tolerance.to_compare_spec()
def load_contract(path: Union[str, Path]) -> BenchmarkContract:
    """Load a BenchmarkContract from a .json file and validate it."""
    p = Path(path)
    if p.suffix.lower() != ".json":
        raise ValueError(f"unsupported contract format {p.suffix!r}; expected .json")
    try:
        obj = __import__("json").loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise FileNotFoundError(f"contract file not found: {p}") from e
    except Exception as e:
        raise ValueError(f"invalid JSON in contract file: {p}") from e
    if not isinstance(obj, dict):
        raise TypeError("top-level contract JSON must be an object")
    c = BenchmarkContract.from_dict(obj)
    c.validate()
    return c
