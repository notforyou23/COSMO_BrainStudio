from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest
def _reload_outputs(monkeypatch) -> object:
    if "src.outputs" in sys.modules:
        del sys.modules["src.outputs"]
    import src.outputs as outputs  # type: ignore
    return importlib.reload(outputs)
def test_output_dir_env_override(monkeypatch, tmp_path):
    out = tmp_path / "artifacts_env"
    monkeypatch.setenv("OUTPUT_DIR", str(out))
    outputs = _reload_outputs(monkeypatch)
    assert Path(outputs.OUTPUT_DIR) == out.resolve()
def test_output_dir_default_resolves_from_cwd(monkeypatch, tmp_path):
    monkeypatch.delenv("OUTPUT_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    outputs = _reload_outputs(monkeypatch)
    assert Path(outputs.OUTPUT_DIR) == (tmp_path / "outputs").resolve()
def test_ensure_dir_creates_directory(monkeypatch, tmp_path):
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "od"))
    outputs = _reload_outputs(monkeypatch)

    d = outputs.ensure_dir("nested/dir")
    assert isinstance(d, Path)
    assert d == (Path(outputs.OUTPUT_DIR) / "nested/dir").resolve()
    assert d.exists() and d.is_dir()
def test_write_text_writes_under_output_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "od"))
    outputs = _reload_outputs(monkeypatch)

    p = outputs.write_text("a/b.txt", "hello")
    expected = (Path(outputs.OUTPUT_DIR) / "a/b.txt").resolve()
    assert Path(p) == expected
    assert expected.read_text(encoding="utf-8") == "hello" 
def test_write_json_writes_under_output_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "od"))
    outputs = _reload_outputs(monkeypatch)

    obj = {"x": 1, "y": ["a", "b"]}
    p = outputs.write_json("meta/run.json", obj)
    expected = (Path(outputs.OUTPUT_DIR) / "meta/run.json").resolve()
    assert Path(p) == expected
    data = expected.read_text(encoding="utf-8")
    loaded = __import__("json").loads(data)
    assert loaded == obj
