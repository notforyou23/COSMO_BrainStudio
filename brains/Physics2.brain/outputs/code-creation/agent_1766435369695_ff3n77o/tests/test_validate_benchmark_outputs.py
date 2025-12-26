import json
from pathlib import Path

import pytest

from tools.validate_benchmark_outputs import main
def _write_json(p: Path, obj) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p
def test_validation_success_explicit_file(tmp_path, capsys):
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://example.com/benchmark.schema.json",
        "type": "object",
        "required": ["$schema", "schema_version", "benchmark", "results"],
        "properties": {
            "$schema": {"type": "string"},
            "schema_version": {"type": "string"},
            "benchmark": {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}},
            "results": {"type": "object"},
        },
    }
    schema_path = _write_json(tmp_path / "schema.json", schema)
    out_path = _write_json(
        tmp_path / "bench_output.json",
        {"$schema": schema["$id"], "schema_version": "1.0", "benchmark": {"name": "demo"}, "results": {}},
    )

    rc = main([str(out_path), "--schema", str(schema_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "Checked 1 file(s): OK" in captured.out
    assert captured.err == ""
def test_validation_failure_and_legacy_detection(tmp_path, capsys):
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://example.com/benchmark.schema.json",
        "type": "object",
        "required": ["$schema", "schema_version"],
        "properties": {"$schema": {"type": "string"}, "schema_version": {"type": "string"}},
    }
    schema_path = _write_json(tmp_path / "schema.json", schema)

    legacy_like = tmp_path / "results.json"
    legacy_like.write_text("{}", encoding="utf-8")

    rc = main([str(legacy_like), "--schema", str(schema_path)])
    captured = capsys.readouterr()
    assert rc == 1
    assert "VALIDATION_FAILED:" in captured.out
    assert str(legacy_like) in captured.err
    assert "deprecated legacy/ad-hoc format" in captured.err
    assert "Checked 1 file(s): FAIL" in captured.err
def test_deterministic_error_ordering(tmp_path, capsys):
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://example.com/benchmark.schema.json",
        "type": "object",
        "required": ["x", "y"],
        "properties": {"x": {"type": "integer"}, "y": {"type": "string"}},
        "additionalProperties": False,
    }
    schema_path = _write_json(tmp_path / "schema.json", schema)
    bad_path = _write_json(tmp_path / "out.json", {"x": "nope"})

    rc = main([str(bad_path), "--schema", str(schema_path)])
    captured = capsys.readouterr()
    assert rc == 1

    err_lines = [ln for ln in captured.err.splitlines() if ln.startswith(" - ")]
    assert len(err_lines) >= 2
    assert f"{bad_path}:$:" in err_lines[0]
    assert "missing required field(s)" in err_lines[0]
    assert f"{bad_path}:$.x:" in err_lines[1]
    assert "is not of type" in err_lines[1]
def test_fail_on_empty_discovery(tmp_path, monkeypatch, capsys):
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://example.com/benchmark.schema.json",
        "type": "object",
    }
    schema_path = _write_json(tmp_path / "schema.json", schema)
    monkeypatch.chdir(tmp_path)

    rc = main(["--schema", str(schema_path), "--fail-on-empty"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "No benchmark output JSON files discovered" in captured.err
