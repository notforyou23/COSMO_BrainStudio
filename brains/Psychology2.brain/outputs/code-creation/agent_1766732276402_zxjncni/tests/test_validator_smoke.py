import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _paths():
    root = _project_root()
    schema = root / "outputs" / "annotation_schema_v0.1.json"
    codebook = root / "outputs" / "task_taxonomy_codebook_v0.1.json"
    example = root / "outputs" / "annotation_example_v0.1.jsonl"
    validator_py = root / "src" / "validator.py"
    return root, schema, codebook, example, validator_py


def _load_first_example(example_path: Path):
    if example_path.exists():
        for line in example_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                return json.loads(line)
    return None


def _generate_minimal_from_schema(schema_path: Path) -> dict:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    props = schema.get("properties", {})
    required = schema.get("required", [])
    rec = {}
    for k in required:
        ps = props.get(k, {})
        if "const" in ps:
            rec[k] = ps["const"]
        elif "enum" in ps and ps["enum"]:
            rec[k] = ps["enum"][0]
        else:
            t = ps.get("type")
            if t == "string" or t is None:
                rec[k] = "x"
            elif t == "integer":
                rec[k] = 1
            elif t == "number":
                rec[k] = 1.0
            elif t == "boolean":
                rec[k] = True
            elif t == "array":
                rec[k] = []
            elif t == "object":
                rec[k] = {}
            else:
                rec[k] = "x"
    return rec


def _candidate_commands(input_path: Path, schema: Path, codebook: Path, validator_py: Path):
    py = sys.executable
    base_invocations = [
        [py, str(validator_py)],
        [py, "-m", "src.validator"],
    ]
    arg_variants = [
        ["--schema", str(schema), "--codebook", str(codebook), str(input_path)],
        [str(input_path), "--schema", str(schema), "--codebook", str(codebook)],
        ["validate", str(input_path), "--schema", str(schema), "--codebook", str(codebook)],
        ["--schema", str(schema), str(input_path)],
        [str(input_path), "--schema", str(schema)],
    ]
    for base in base_invocations:
        for args in arg_variants:
            yield base + args


def _run_any_valid_command(input_path: Path, schema: Path, codebook: Path, validator_py: Path):
    last = None
    for cmd in _candidate_commands(input_path, schema, codebook, validator_py):
        try:
            p = subprocess.run(cmd, capture_output=True, text=True)
        except Exception as e:
            last = ("EXC", cmd, str(e))
            continue
        if p.returncode == 0:
            return cmd
        last = (p.returncode, cmd, (p.stdout or "") + (p.stderr or ""))
    raise AssertionError(f"Could not find a working validator invocation. Last={last!r}")


def _run(cmd, input_path: Path):
    p = subprocess.run(cmd[:-1] + [str(input_path)], capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


@pytest.mark.smoke
def test_validator_smoke_valid_and_invalid(tmp_path: Path):
    root, schema, codebook, example, validator_py = _paths()
    assert schema.exists(), f"Missing schema: {schema}"
    assert codebook.exists(), f"Missing codebook: {codebook}"
    assert validator_py.exists() or (root / "src" / "validator.py").exists(), "Missing validator script"

    rec = _load_first_example(example)
    if rec is None:
        rec = _generate_minimal_from_schema(schema)

    valid_path = tmp_path / "valid.jsonl"
    valid_path.write_text(json.dumps(rec) + "\n", encoding="utf-8")

    cmd = _run_any_valid_command(valid_path, schema, codebook, validator_py)
    rc, out = _run(cmd, valid_path)
    assert rc == 0, f"Expected valid input to pass. cmd={cmd} out={out}"

    schema_obj = json.loads(schema.read_text(encoding="utf-8"))
    required = list(schema_obj.get("required", []))
    assert required, "Schema must define required fields for this smoke test"
    missing_key = required[0]
    invalid_missing = dict(rec)
    invalid_missing.pop(missing_key, None)
    invalid_missing_path = tmp_path / "invalid_missing.jsonl"
    invalid_missing_path.write_text(json.dumps(invalid_missing) + "\n", encoding="utf-8")

    rc, out = _run(cmd, invalid_missing_path)
    assert rc != 0, f"Expected missing required field to fail. missing={missing_key} out={out}"

    invalid_category = dict(rec)
    props = schema_obj.get("properties", {})
    enum_field = None
    for k, ps in props.items():
        if isinstance(ps, dict) and "enum" in ps and isinstance(ps["enum"], list) and ps["enum"]:
            enum_field = k
            break
    if enum_field:
        invalid_category[enum_field] = "__INVALID_ENUM_VALUE__"
        invalid_enum_path = tmp_path / "invalid_enum.jsonl"
        invalid_enum_path.write_text(json.dumps(invalid_category) + "\n", encoding="utf-8")
        rc, out = _run(cmd, invalid_enum_path)
        assert rc != 0, f"Expected invalid enum value to fail. field={enum_field} out={out}"
