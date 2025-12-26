from __future__ import annotations

from pathlib import Path

import pytest

from src import benchmark_contract as bc
def _minimal_contract(*, output_file: str = "outputs.json", golden_file: str = "golden.json", input_file: str | None = None):
    io = {"output_file": output_file, "golden_file": golden_file}
    if input_file is not None:
        io["input_file"] = input_file
    return {
        "contract_version": bc.CONTRACT_VERSION,
        "metadata": {"task_id": "t0", "task_name": "task"},
        "io": io,
        "reference": {"algorithm": "echo"},
        "tolerance": {"abs": 1e-8, "rel": 1e-6, "nan_equal": True},
    }
def test_validate_contract_accepts_minimal_schema():
    c = _minimal_contract()
    bc.validate_contract(c)  # should not raise
@pytest.mark.parametrize(
    "mutator, exc",
    [
        (lambda c: c.pop("contract_version"), ValueError),
        (lambda c: c.__setitem__("contract_version", "v9.9"), ValueError),
        (lambda c: c.pop("metadata"), ValueError),
        (lambda c: c.__setitem__("metadata", "nope"), TypeError),
        (lambda c: c["metadata"].pop("task_id"), ValueError),
        (lambda c: c.pop("io"), ValueError),
        (lambda c: c["io"].pop("output_file"), ValueError),
        (lambda c: c["io"].pop("golden_file"), ValueError),
        (lambda c: c.pop("reference"), ValueError),
        (lambda c: c.__setitem__("reference", []), TypeError),
        (lambda c: c["reference"].pop("algorithm"), ValueError),
        (lambda c: c.__setitem__("tolerance", "bad"), TypeError),
    ],
)
def test_validate_contract_rejects_schema_violations(mutator, exc):
    c = _minimal_contract()
    mutator(c)
    with pytest.raises(exc):
        bc.validate_contract(c)
def test_load_contract_round_trip(tmp_path: Path):
    p = tmp_path / "contract.json"
    p.write_text(__import__("json").dumps(_minimal_contract()), encoding="utf-8")
    loaded = bc.load_contract(p)
    assert loaded["contract_version"] == bc.CONTRACT_VERSION
    assert loaded["metadata"]["task_id"] == "t0"
def test_resolve_io_paths_places_output_under_run_dir_and_resolves(tmp_path: Path):
    project_root = tmp_path
    run_dir = Path("runs/x")
    c = _minimal_contract(output_file="out/output.json", golden_file="golden/g.json", input_file="inputs/i.json")

    out_p, gold_p, in_p = bc.resolve_io_paths(c, project_root, run_dir=run_dir)

    assert out_p.is_absolute() and gold_p.is_absolute()
    assert str(out_p).endswith(str(run_dir / "out/output.json"))
    assert gold_p == (project_root / "golden/g.json").resolve()
    assert in_p == (project_root / "inputs/i.json").resolve()
def test_validate_artifact_paths_enforces_file_existence_and_creates_output_dir(tmp_path: Path):
    out_p = tmp_path / "runs/latest/out/output.json"
    gold_p = tmp_path / "golden.json"
    in_p = tmp_path / "inputs.json"

    with pytest.raises(FileNotFoundError):
        bc.validate_artifact_paths(out_p, gold_p)

    gold_p.write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        bc.validate_artifact_paths(out_p, gold_p, in_p)

    in_p.write_text("{}", encoding="utf-8")
    bc.validate_artifact_paths(out_p, gold_p, in_p)

    assert out_p.parent.exists()
