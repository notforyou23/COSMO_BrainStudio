import sys
from pathlib import Path

import pytest

# Make /src importable as a (namespace) package root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from benchmarks.runner import run_task
def _write_mod(tmp_path: Path, name: str, code: str) -> str:
    mod_path = tmp_path / f"{name}.py"
    mod_path.write_text(code, encoding="utf-8")
    if str(tmp_path) not in sys.path:
        sys.path.insert(0, str(tmp_path))
    return name
def _write_contract(tmp_path: Path, obj: dict) -> Path:
    p = tmp_path / "contract.json"
    p.write_text(__import__("json").dumps(obj), encoding="utf-8")
    return p
def test_runner_refuses_missing_tolerance_documentation(tmp_path: Path):
    _write_mod(
        tmp_path,
        "task_mod",
        "def reference(x):\n    return {'y': float(x)}\n",
    )

    bad = {
        "task_id": "t_bad",
        "version": "0.1",
        "description": "desc",
        "reference": {"callable": "task_mod:reference"},
        "cases": [{"input": 1}],
        "observables": {
            "y": {
                "description": "output",
                "tolerance": {"atol": 0.1},
                "tolerance_notes": "",  # required non-empty
            }
        },
    }
    with pytest.raises(ValueError, match="tolerance_notes"):
        run_task(_write_contract(tmp_path, bad), candidate=lambda x: {"y": float(x)})
def test_runner_applies_contract_defined_tolerances(tmp_path: Path):
    _write_mod(
        tmp_path,
        "task_mod2",
        "def reference(x):\n    return {'y': 1.0}\n",
    )

    contract = {
        "task_id": "t_ok",
        "version": "0.1",
        "description": "desc",
        "reference": {"callable": "task_mod2:reference"},
        "cases": [{"input": 0}],
        "observables": {
            "y": {
                "description": "scalar output",
                "tolerance": {"atol": 0.1, "rtol": 0.0},
                "tolerance_notes": "Reference uses float math; allow small absolute drift.",
            }
        },
    }

    # Candidate differs by 0.05: must pass under atol=0.1.
    res = run_task(_write_contract(tmp_path, contract), candidate=lambda x: {"y": 1.05})
    assert res.passed, res.failures

    # Tighten tolerance: now must fail.
    contract["observables"]["y"]["tolerance"]["atol"] = 0.01
    res2 = run_task(_write_contract(tmp_path, contract), candidate=lambda x: {"y": 1.05})
    assert not res2.passed
    assert res2.failures and "y" in res2.failures[0]
