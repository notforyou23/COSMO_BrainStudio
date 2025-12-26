"""Benchmark contract helpers for v0.1 tasks.

This module standardizes how benchmarks describe:
- metadata (task id/name, contract version)
- I/O artifact paths (inputs, outputs, golden references)
- reference algorithm selection/interface
- tolerance rules for numeric diffs

It is intentionally small and dependency-free so both tests and CLIs can share it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Protocol, Tuple


CONTRACT_VERSION = "v0.1"

# Canonical relative locations (used by the default contract JSON and CLI).
DEFAULT_CONTRACT_PATH = Path("benchmarks/contracts/v0_1.json")
DEFAULT_RUN_DIR = Path("benchmarks/runs/latest")
DEFAULT_GOLDEN_DIR = Path("benchmarks/golden/v0_1")
DEFAULT_OUTPUT_FILE = Path("outputs.json")


class ReferenceAlgorithm(Protocol):
    """Reference algorithm interface used by the benchmark runner.

    Implementations should be pure with respect to the provided input mapping.
    """

    def __call__(self, inputs: Mapping[str, Any]) -> Any: ...


@dataclass(frozen=True)
class Tolerance:
    """Absolute/relative tolerance settings for numeric comparisons."""

    abs: float = 0.0
    rel: float = 0.0
    nan_equal: bool = False

    @classmethod
    def from_obj(cls, obj: Any) -> "Tolerance":
        if obj is None:
            return cls()
        if isinstance(obj, (int, float)):
            return cls(abs=float(obj), rel=0.0)
        if not isinstance(obj, Mapping):
            raise TypeError("tolerance must be a number or mapping")
        return cls(
            abs=float(obj.get("abs", 0.0) or 0.0),
            rel=float(obj.get("rel", 0.0) or 0.0),
            nan_equal=bool(obj.get("nan_equal", False)),
        )

    def to_obj(self) -> Dict[str, Any]:
        return {"abs": self.abs, "rel": self.rel, "nan_equal": self.nan_equal}


def _require(m: Mapping[str, Any], key: str) -> Any:
    if key not in m:
        raise ValueError(f"contract missing required field: {key}")
    return m[key]


def load_contract(path: Path) -> Dict[str, Any]:
    """Load a benchmark contract JSON file."""
    data = json_load(path)
    validate_contract(data)
    return data


def json_load(path: Path) -> Any:
    text = Path(path).read_text(encoding="utf-8")
    return __import__("json").loads(text)


def validate_contract(contract: Mapping[str, Any]) -> None:
    """Validate minimum schema for a v0.1 benchmark contract."""
    version = _require(contract, "contract_version")
    if version != CONTRACT_VERSION:
        raise ValueError(f"unsupported contract_version={version!r} (expected {CONTRACT_VERSION})")

    meta = _require(contract, "metadata")
    if not isinstance(meta, Mapping):
        raise TypeError("metadata must be an object")
    _require(meta, "task_id")
    _require(meta, "task_name")

    io = _require(contract, "io")
    if not isinstance(io, Mapping):
        raise TypeError("io must be an object")
    # Inputs may be absent for some tasks, but output/golden paths must be present.
    _require(io, "output_file")
    _require(io, "golden_file")

    tol = contract.get("tolerance", {})
    Tolerance.from_obj(tol)  # type-check only

    ref = _require(contract, "reference")
    if not isinstance(ref, Mapping):
        raise TypeError("reference must be an object")
    _require(ref, "algorithm")


def resolve_io_paths(
    contract: Mapping[str, Any],
    project_root: Path,
    run_dir: Optional[Path] = None,
) -> Tuple[Path, Path, Optional[Path]]:
    """Resolve I/O paths from a contract.

    Returns (output_path, golden_path, inputs_path_or_None).
    """
    io = contract["io"]
    out_rel = Path(io["output_file"])
    gold_rel = Path(io["golden_file"])
    inp = io.get("input_file")
    inputs_rel = Path(inp) if inp else None

    run_dir = run_dir or DEFAULT_RUN_DIR
    output_path = (project_root / run_dir / out_rel).resolve()
    golden_path = (project_root / gold_rel).resolve()
    inputs_path = (project_root / inputs_rel).resolve() if inputs_rel else None
    return output_path, golden_path, inputs_path


def get_tolerance(contract: Mapping[str, Any]) -> Tolerance:
    """Return the contract's tolerance settings."""
    return Tolerance.from_obj(contract.get("tolerance", {}))


def validate_artifact_paths(
    output_path: Path,
    golden_path: Path,
    inputs_path: Optional[Path] = None,
) -> None:
    """Validate benchmark artifact file existence/parent dirs."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not golden_path.exists():
        raise FileNotFoundError(f"golden file not found: {golden_path}")
    if inputs_path is not None and not inputs_path.exists():
        raise FileNotFoundError(f"input file not found: {inputs_path}")
