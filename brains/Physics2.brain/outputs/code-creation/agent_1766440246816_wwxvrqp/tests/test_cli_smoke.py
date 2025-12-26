import json
from pathlib import Path

import pytest


def _repo_root() -> Path:
    # tests/ is expected to live at <repo_root>/tests
    return Path(__file__).resolve().parents[1]
def test_cli_import_and_parser_builds():
    # Import should not raise (guards against syntax errors).
    import qg_bench.cli as cli

    parser = cli.build_parser()
    # Basic sanity: expected subcommands exist.
    sub_actions = [a for a in parser._actions if a.dest == "cmd"]
    assert sub_actions, "CLI parser is missing required subcommand configuration"
def test_cli_validate_example_payload_exits_zero(capsys):
    import qg_bench.cli as cli

    example = _repo_root() / "outputs" / "examples" / "benchmark_case_001.json"
    assert example.is_file()

    code = cli.main(["validate", str(example)])
    out = capsys.readouterr()
    assert code == 0
    # validate should be quiet on success
    assert out.err == ""
def test_cli_run_dry_run_prints_plan_and_exits_zero(tmp_path, capsys):
    import qg_bench.cli as cli

    payload = {
        "case_id": "smoke_case",
        "experiment": {"name": "toy_ising_emergent_classicality", "params": {"seed": 0}},
    }
    inp = tmp_path / "case.json"
    inp.write_text(json.dumps(payload), encoding="utf-8")

    code = cli.main(["run", str(inp), "--dry-run"])
    captured = capsys.readouterr()

    assert code == 0
    data = json.loads(captured.out)
    assert data["case_id"] == "smoke_case"
    assert data["status"] == "planned"
