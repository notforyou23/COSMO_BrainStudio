from __future__ import annotations

from pathlib import Path
import json
import pytest
def _project_root() -> Path:
    # tests/.. is assumed to be repository root
    return Path(__file__).resolve().parents[1]


def _find_outputs_dir(root: Path) -> Path:
    for name in ("outputs", "output", "out"):
        p = root / name
        if p.is_dir():
            return p
    # fallback: first directory containing at least one JSON file
    for p in sorted(root.rglob("*")):
        if p.is_dir():
            try:
                if any(c.suffix == ".json" for c in p.iterdir() if c.is_file()):
                    return p
            except PermissionError:
                continue
    return root / "outputs"  # will fail with a clear assertion


def _iter_json_files(outputs_dir: Path) -> list[Path]:
    files = sorted({*outputs_dir.glob("*.json"), *outputs_dir.rglob("*.json")})
    return [p for p in files if p.is_file()]
def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        return json.loads(path.read_text(encoding="utf-8-sig"))


def _has_list_of_dicts(obj) -> bool:
    if isinstance(obj, list):
        return len(obj) > 0 and all(isinstance(x, dict) for x in obj)
    if isinstance(obj, dict):
        return any(_has_list_of_dicts(v) for v in obj.values())
    return False


def _assert_scriptish_schema(data):
    assert data is not None
    assert isinstance(data, (dict, list)), f"Expected dict/list JSON, got {type(data)}"
    # Prefer known top-level keys when present; otherwise accept any nested list-of-dicts.
    if isinstance(data, dict):
        assert data, "Top-level JSON object is empty"
        for key in ("scenes", "steps", "events", "items", "segments"):
            if key in data:
                assert isinstance(data[key], list), f"{key} must be a list"
                assert data[key], f"{key} must be non-empty"
                assert all(isinstance(x, dict) for x in data[key]), f"{key} elements must be objects"
                return
        assert _has_list_of_dicts(data), "Could not find any list-of-objects in JSON"
    else:
        assert data, "Top-level JSON array is empty"
        assert any(isinstance(x, dict) for x in data), "Top-level JSON array has no objects"
def test_outputs_directory_has_artifacts():
    root = _project_root()
    outputs = _find_outputs_dir(root)
    assert outputs.is_dir(), f"Outputs directory not found: {outputs}"
    files = [p for p in outputs.rglob("*") if p.is_file()]
    assert files, f"No files found under outputs directory: {outputs}"


def test_at_least_one_json_artifact_parses_and_looks_like_a_script():
    root = _project_root()
    outputs = _find_outputs_dir(root)
    json_paths = _iter_json_files(outputs)
    assert json_paths, f"No JSON artifacts found in: {outputs}"

    # Smoke-test up to 3 JSON files so a single non-script JSON doesn't fail the suite.
    checked = 0
    for path in json_paths[:3]:
        data = _load_json(path)
        _assert_scriptish_schema(data)
        checked += 1
    assert checked >= 1
@pytest.mark.parametrize("must_exist_name", ["outputs", "output", "out"])
def test_common_outputs_directory_name_is_present_or_json_found(must_exist_name: str):
    root = _project_root()
    candidate = root / must_exist_name
    outputs = _find_outputs_dir(root)
    # Either the common directory exists, or the fallback found a directory with JSON.
    assert candidate.is_dir() or outputs.is_dir()
