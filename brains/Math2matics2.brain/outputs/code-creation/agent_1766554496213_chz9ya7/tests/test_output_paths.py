from __future__ import annotations

import importlib
import inspect
import os
from pathlib import Path

import pytest


def _output_module():
    return importlib.import_module("src.output_paths")


def _call_get_output_dir(*, create: bool = True) -> Path:
    mod = _output_module()
    candidates = [
        "get_output_dir",
        "output_dir",
        "get_outputs_dir",
        "outputs_dir",
        "resolve_output_dir",
        "resolve_outputs_dir",
    ]
    fn = None
    for name in candidates:
        if hasattr(mod, name):
            fn = getattr(mod, name)
            break
    if fn is None or not callable(fn):
        raise AssertionError("Expected src.output_paths to expose an output-dir helper (e.g., get_output_dir).")

    sig = inspect.signature(fn)
    kwargs = {}
    for k in ("create", "mkdir", "ensure", "ensure_dir", "make_dirs"):
        if k in sig.parameters:
            kwargs[k] = create
            break
    return Path(fn(**kwargs))


def test_default_outputs_dir_is_relative_to_cwd_and_created(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OUTPUT_DIR", raising=False)

    out_dir = _call_get_output_dir(create=True)
    expected = (tmp_path / "outputs").resolve()
    got = out_dir.resolve()

    assert got == expected
    assert got.is_dir()
    assert str(got) != "/outputs"
    assert not str(got).startswith("/outputs" + os.sep)


def test_output_dir_can_be_overridden_via_env_and_created(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    custom = tmp_path / "my_outputs"
    monkeypatch.setenv("OUTPUT_DIR", str(custom))

    out_dir = _call_get_output_dir(create=True)

    assert out_dir.resolve() == custom.resolve()
    assert out_dir.is_dir()


@pytest.mark.parametrize("bad", ["/outputs", "/outputs/", "/outputs/subdir"])
def test_rejects_absolute_outputs_root_targets(bad, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OUTPUT_DIR", bad)

    with pytest.raises((ValueError, AssertionError)):
        _call_get_output_dir(create=True)
