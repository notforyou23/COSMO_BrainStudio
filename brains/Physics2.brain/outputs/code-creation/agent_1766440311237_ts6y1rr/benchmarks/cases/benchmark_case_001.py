"""benchmark_case_001

A small deterministic benchmark case that produces JSON-like expected/actual
results suitable for tolerance-aware recursive comparison.

The runner applies the global determinism policy; this case additionally uses a
local RNG keyed by the provided seed to make its payload generation explicit and
repeatable.
"""

from __future__ import annotations

import json
import math
import random
from typing import Any, Dict, List, Mapping

from src.stable_json import normalize
def _make_payload(seed: int) -> Dict[str, Any]:
    rng = random.Random(seed)

    # Generate values with a mix of magnitudes to exercise numeric comparison.
    values: List[float] = []
    for i in range(50):
        # Deterministic but "noisy" signal.
        base = math.sin((i + 1) * 0.1) + math.cos((i + 1) * 0.07)
        jitter = (rng.random() - 0.5) * 1e-6
        values.append(base + jitter)

    # Use both sum and fsum to create stable, well-conditioned stats.
    s = float(math.fsum(values))
    mean = s / len(values)
    var = float(math.fsum((v - mean) ** 2 for v in values)) / len(values)

    payload: Dict[str, Any] = {
        "case": "benchmark_case_001",
        "seed": seed,
        "values": values,
        "stats": {
            "count": len(values),
            "sum": s,
            "mean": mean,
            "variance": var,
            "min": min(values),
            "max": max(values),
        },
        # Include nested structure and key-order variability to ensure stability.
        "nested": {
            "b": {"x": 1, "y": 2.0, "z": [3, 4.0]},
            "a": [{"k": "v", "n": 1.25}, {"k": "w", "n": -0.0}],
        },
    }
    return payload
def run(*, seed: int, stable_dumps) -> Mapping[str, Any]:
    """Return {expected, actual, ...} for the benchmark runner.

    expected:
        Canonically normalized JSON-like structure.
    actual:
        Round-trip through stable JSON to ensure deterministic serialization.
    """
    raw = _make_payload(seed)

    expected = normalize(raw, float_precision=15)
    # Serialize using the runner-provided stable_dumps for determinism,
    # then parse back to a structure for tolerance-aware comparison.
    actual = json.loads(stable_dumps(raw))

    return {
        "expected": expected,
        "actual": actual,
        "metadata": {
            "float_precision": 15,
            # Helps debug without relying on dict ordering.
            "expected_json": stable_dumps(expected),
        },
    }
