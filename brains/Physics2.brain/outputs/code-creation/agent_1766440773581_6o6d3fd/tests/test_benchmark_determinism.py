from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


# Allow importing the project modules when the package isn't installed.
SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from benchmark_compare import compare_files, compare_results  # noqa: E402
from benchmark_determinism import DeterminismPolicy  # noqa: E402
from benchmark_runner import run_benchmark, write_benchmark_result  # noqa: E402


def _benchmark_payload() -> dict:
    \"\"\"Produce RNG-driven output to validate deterministic seeding.\"\"\"
    import random

    out = {
        "py_random": [random.random() for _ in range(5)],
        "nested": {"a": random.randint(0, 10), "b": [random.random(), 1.0 / 3.0]},
    }

    # If numpy exists in the environment, include it too (best-effort).
    try:
        import numpy as np  # type: ignore

        out["np_random"] = np.random.RandomState().rand(3).tolist()
    except Exception:
        out["np_random"] = None

    return out


def test_benchmark_deterministic_bytes_and_json(tmp_path: Path) -> None:
    policy = DeterminismPolicy(seed=123, float_format=".12g", sort_keys=True, ensure_ascii=False)

    r1 = run_benchmark(_benchmark_payload, policy=policy)
    r2 = run_benchmark(_benchmark_payload, policy=policy)

    b1 = policy.dump_bytes(r1)
    b2 = policy.dump_bytes(r2)
    assert b1 == b2  # byte-identical canonical JSON under the deterministic policy

    # Structural equality under shared comparator rules (exact comparison).
    compare_results(r1, r2, tolerance=None)

    # Also verify determinism across file IO (canonical bytes are identical).
    p1 = tmp_path / "run1.json"
    p2 = tmp_path / "run2.json"
    write_benchmark_result(str(p1), r1, policy=policy)
    write_benchmark_result(str(p2), r2, policy=policy)
    assert p1.read_bytes() == p2.read_bytes()
    compare_files(p1, p2, tolerance=None)

    # Sanity: files are valid JSON and re-load to the same structure.
    assert json.loads(p1.read_text(encoding="utf-8")) == r1
