"""Contract data model + JSON Schemas for COSMO benchmark contracts.

A contract is attached per v0.1 benchmark and is used to:
- declare required metadata
- provide a reference algorithm/pseudocode
- state output invariants
- define tolerance policy for numeric comparisons
- ship canonical test vectors
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
# JSON Schema (draft 2020-12) for a benchmark contract document.
CONTRACT_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://cosmo-benchmarks.dev/schemas/contract.schema.json",
    "title": "COSMO Benchmark Contract",
    "type": "object",
    "required": ["metadata", "reference", "invariants", "tolerance_policy", "test_vectors"],
    "additionalProperties": False,
    "properties": {
        "metadata": {
            "type": "object",
            "required": ["benchmark_id", "benchmark_version", "title", "description"],
            "additionalProperties": False,
            "properties": {
                "benchmark_id": {"type": "string", "minLength": 1},
                "benchmark_version": {"type": "string", "minLength": 1},
                "title": {"type": "string", "minLength": 1},
                "description": {"type": "string", "minLength": 1},
                "tags": {"type": "array", "items": {"type": "string"}, "default": []},
                "authors": {"type": "array", "items": {"type": "string"}, "default": []},
                "license": {"type": "string"},
                "source": {"type": "string", "description": "Citation / URL / paper reference."},
            },
        },
        "reference": {
            "type": "object",
            "required": ["algorithm", "pseudocode"],
            "additionalProperties": False,
            "properties": {
                "algorithm": {"type": "string", "minLength": 1},
                "pseudocode": {"type": "string", "minLength": 1},
                "notes": {"type": "string"},
            },
        },
        "invariants": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["name", "statement"],
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "statement": {"type": "string", "minLength": 1},
                    "scope": {"type": "string", "default": "output"},
                    "severity": {"type": "string", "enum": ["must", "should"], "default": "must"},
                },
            },
        },
        "tolerance_policy": {
            "type": "object",
            "required": ["mode"],
            "additionalProperties": False,
            "properties": {
                "mode": {"type": "string", "enum": ["exact", "absolute", "relative", "abs+rel"]},
                "atol": {"type": "number", "minimum": 0, "default": 0.0},
                "rtol": {"type": "number", "minimum": 0, "default": 0.0},
                "nan_equal": {"type": "boolean", "default": False},
                "explain": {"type": "string", "description": "Human-readable policy rationale."},
            },
            "allOf": [
                {
                    "if": {"properties": {"mode": {"const": "exact"}}},
                    "then": {"properties": {"atol": {"const": 0.0}, "rtol": {"const": 0.0}}},
                },
                {
                    "if": {"properties": {"mode": {"enum": ["absolute", "abs+rel"]}}},
                    "then": {"required": ["atol"]},
                },
                {
                    "if": {"properties": {"mode": {"enum": ["relative", "abs+rel"]}}},
                    "then": {"required": ["rtol"]},
                },
            ],
        },
        "test_vectors": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["id", "inputs", "expected"],
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "inputs": {"type": "object"},
                    "expected": {"type": "object"},
                    "notes": {"type": "string"},
                },
            },
        },
    },
}
# JSON Schema for a contributed implementation's compliance report.
COMPLIANCE_REPORT_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://cosmo-benchmarks.dev/schemas/compliance_report.schema.json",
    "title": "COSMO Contract Compliance Report",
    "type": "object",
    "required": ["benchmark_id", "benchmark_version", "implementation_id", "passed", "results"],
    "additionalProperties": False,
    "properties": {
        "benchmark_id": {"type": "string", "minLength": 1},
        "benchmark_version": {"type": "string", "minLength": 1},
        "implementation_id": {"type": "string", "minLength": 1},
        "passed": {"type": "boolean"},
        "summary": {"type": "string"},
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["test_vector_id", "passed"],
                "additionalProperties": False,
                "properties": {
                    "test_vector_id": {"type": "string", "minLength": 1},
                    "passed": {"type": "boolean"},
                    "diagnostics": {"type": "object"},
                },
            },
        },
    },
}
@dataclass(frozen=True)
class Invariant:
    name: str
    statement: str
    scope: str = "output"
    severity: str = "must"


@dataclass(frozen=True)
class TolerancePolicy:
    mode: str  # exact|absolute|relative|abs+rel
    atol: float = 0.0
    rtol: float = 0.0
    nan_equal: bool = False
    explain: str = ""


@dataclass(frozen=True)
class TestVector:
    id: str
    inputs: Dict[str, Any]
    expected: Dict[str, Any]
    notes: str = ""


@dataclass(frozen=True)
class Contract:
    metadata: Dict[str, Any]
    reference: Dict[str, Any]
    invariants: List[Invariant]
    tolerance_policy: TolerancePolicy
    test_vectors: List[TestVector] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["invariants"] = [asdict(x) for x in self.invariants]
        d["tolerance_policy"] = asdict(self.tolerance_policy)
        d["test_vectors"] = [asdict(x) for x in self.test_vectors]
        return d
def validate_against_schema(obj: Dict[str, Any], schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate with jsonschema if available; otherwise perform minimal checks."""
    try:
        import jsonschema  # type: ignore
        try:
            jsonschema.validate(instance=obj, schema=schema)
            return True, []
        except Exception as e:  # jsonschema.ValidationError or SchemaError
            return False, [str(e)]
    except Exception:
        # Minimal structural validation (keeps this package dependency-light).
        missing = [k for k in schema.get("required", []) if k not in obj]
        if missing:
            return False, [f"missing required keys: {missing}"]
        if schema.get("additionalProperties") is False:
            allowed = set(schema.get("properties", {}).keys())
            extra = sorted([k for k in obj.keys() if k not in allowed])
            if extra:
                return False, [f"unexpected keys: {extra}"]
        return True, []


__all__ = [
    "CONTRACT_SCHEMA",
    "COMPLIANCE_REPORT_SCHEMA",
    "Contract",
    "Invariant",
    "TolerancePolicy",
    "TestVector",
    "validate_against_schema",
]
