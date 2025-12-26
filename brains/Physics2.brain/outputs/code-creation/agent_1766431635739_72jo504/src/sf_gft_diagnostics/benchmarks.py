"""Benchmark templates and reference comparisons for SF/GFT diagnostics.

This module provides small, standardized benchmark specifications with
reference values and evaluation protocols. Benchmarks are intentionally
model-agnostic: they define *what to measure* and *how to score it*, not
how to run a particular RG/tensor-network/spinfoam code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Sequence, Tuple, Union

import math

Number = Union[int, float]
ArrayLike = Sequence[Number]
ResultDict = Mapping[str, Any]
ScoreDict = Dict[str, float]
@dataclass(frozen=True)
class BenchmarkSpec:
    """A benchmark problem with a minimal evaluation protocol.

    - `required`: keys expected in a results dict produced by the user's pipeline.
    - `reference`: reference values/distributions for comparison.
    - `scorers`: mapping from score-name to callable(result, reference)->float (lower is better).
    """

    name: str
    description: str
    required: Tuple[str, ...]
    reference: Dict[str, Any]
    scorers: Dict[str, Callable[[ResultDict, Dict[str, Any]], float]] = field(default_factory=dict)

    def evaluate(self, result: ResultDict) -> ScoreDict:
        missing = [k for k in self.required if k not in result]
        if missing:
            raise KeyError(f"Missing required result keys for {self.name}: {missing}")
        return {k: float(fn(result, self.reference)) for k, fn in self.scorers.items()}
def _abs_rel_err(x: float, xref: float, eps: float = 1e-12) -> float:
    return abs(x - xref) / (abs(xref) + eps)


def _curve_l2(y: ArrayLike, yref: ArrayLike) -> float:
    if len(y) != len(yref) or len(y) == 0:
        raise ValueError("Curve lengths must match and be non-empty")
    return math.sqrt(sum((float(a) - float(b)) ** 2 for a, b in zip(y, yref)) / len(y))


def _score_critical_point(result: ResultDict, ref: Dict[str, Any]) -> float:
    return _abs_rel_err(float(result["critical_point"]), float(ref["critical_point"]))


def _score_exponents(result: ResultDict, ref: Dict[str, Any]) -> float:
    exps = result["exponents"]
    rexps = ref["exponents"]
    keys = sorted(set(rexps) & set(exps))
    if not keys:
        raise KeyError("No overlapping exponent keys between result and reference")
    return sum(_abs_rel_err(float(exps[k]), float(rexps[k])) for k in keys) / len(keys)


def _score_two_point_shape(result: ResultDict, ref: Dict[str, Any]) -> float:
    # Compare normalized correlator shapes at common distances/momenta.
    y = [float(v) for v in result["two_point"]]
    yref = [float(v) for v in ref["two_point_ref"]]
    sy, sref = sum(abs(v) for v in y), sum(abs(v) for v in yref)
    y = [v / (sy + 1e-12) for v in y]
    yref = [v / (sref + 1e-12) for v in yref]
    return _curve_l2(y, yref)


def _score_flatness(result: ResultDict, ref: Dict[str, Any]) -> float:
    # Semiclassical Regge-like: deficit angles ~ 0; score mean absolute curvature proxy.
    deficits = [abs(float(x)) for x in result["deficit_angles"]]
    return sum(deficits) / max(1, len(deficits)) / float(ref.get("scale", 1.0))
def benchmark_ising2d() -> BenchmarkSpec:
    """2D Ising universality: exact Tc and exponents for RG cross-validation."""
    tc = 2.0 / math.log(1.0 + math.sqrt(2.0))
    ref = {
        "critical_point": tc,
        "exponents": {"nu": 1.0, "beta": 0.125, "gamma": 1.75, "eta": 0.25},
        # Optional shape reference: power-law at criticality for r=1..8 (normalized).
        "two_point_ref": [1.0 / (r ** 0.25) for r in range(1, 9)],
    }
    return BenchmarkSpec(
        name="ising2d",
        description="2D Ising exact Tc and exponents; optional correlator-shape check.",
        required=("critical_point", "exponents"),
        reference=ref,
        scorers={
            "critical_point_relerr": _score_critical_point,
            "exponents_mean_relerr": _score_exponents,
        },
    )


def benchmark_tensor_melonic() -> BenchmarkSpec:
    """Large-N melonic tensor model: solvable critical coupling and susceptibility exponent."""
    # Quartic melonic in many conventions has g_c=1/4 for the reduced SD equation.
    ref = {"critical_point": 0.25, "exponents": {"gamma": 0.5}}
    return BenchmarkSpec(
        name="tensor_melonic",
        description="Toy melonic tensor/GFT-like model with known critical coupling/exponent.",
        required=("critical_point", "exponents"),
        reference=ref,
        scorers={"critical_point_relerr": _score_critical_point, "exponents_mean_relerr": _score_exponents},
    )


def benchmark_regge_flatness() -> BenchmarkSpec:
    """Semiclassical Regge-like limit: deficit angles small for near-flat configurations."""
    ref = {"scale": 1.0}
    return BenchmarkSpec(
        name="regge_flatness",
        description="Deficit-angle flatness diagnostic (mean |epsilon_h|, normalized).",
        required=("deficit_angles",),
        reference=ref,
        scorers={"flatness_mean_abs": _score_flatness},
    )


def benchmark_two_point_shape() -> BenchmarkSpec:
    """Generic correlator-shape comparison against a reference curve."""
    ref = {"two_point_ref": [1.0 / (r ** 2) for r in range(1, 9)]}
    return BenchmarkSpec(
        name="two_point_shape",
        description="Normalized L2 distance between measured and reference 2-pt function shapes.",
        required=("two_point",),
        reference=ref,
        scorers={"two_point_shape_l2": _score_two_point_shape},
    )
def list_benchmarks() -> Tuple[BenchmarkSpec, ...]:
    """Return the default benchmark suite (ordered by broad usefulness)."""
    return (
        benchmark_ising2d(),
        benchmark_tensor_melonic(),
        benchmark_regge_flatness(),
        benchmark_two_point_shape(),
    )


def get_benchmark(name: str) -> BenchmarkSpec:
    """Fetch a benchmark by name."""
    for b in list_benchmarks():
        if b.name == name:
            return b
    raise KeyError(f"Unknown benchmark: {name!r}. Available: {[b.name for b in list_benchmarks()]}")
