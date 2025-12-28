from __future__ import annotations

import inspect
import json
import os
from pathlib import Path

import pytest

import evconv.config as cfg


def _call(func, /, *args, **kwargs):
    sig = inspect.signature(func)
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
        return func(*args, **kwargs)
    filtered = {k: v for k, v in kwargs.items() if k in sig.parameters}
    return func(*args, **filtered)


def _get_default_config():
    for name in ("default_config", "make_default_config", "defaults"):
        if hasattr(cfg, name):
            obj = getattr(cfg, name)
            return obj() if callable(obj) else obj
    raise AssertionError("No default config factory found in evconv.config")
def test_default_assembly_and_validation():
    c = _get_default_config()
    assert isinstance(c, dict)
    assert c, "default config should not be empty"
    validate = getattr(cfg, "validate_config", None) or getattr(cfg, "validate", None)
    if validate is None:
        pytest.skip("validation helper not exposed yet")
    out = _call(validate, c)
    assert out is None or isinstance(out, dict)

    plotting = c.get("plotting") or c.get("plot")
    if plotting is not None:
        assert isinstance(plotting, dict)
def test_deep_merge_behavior():
    merge = getattr(cfg, "merge_config", None) or getattr(cfg, "merge", None) or getattr(cfg, "deep_merge", None)
    if merge is None:
        pytest.skip("merge helper not exposed yet")
    a = {"a": {"b": 1, "keep": True}, "x": 1}
    b = {"a": {"c": 2, "keep": False}, "y": 2}
    merged = _call(merge, a, b)
    assert merged["a"]["b"] == 1
    assert merged["a"]["c"] == 2
    assert merged["a"]["keep"] is False
    assert merged["x"] == 1 and merged["y"] == 2
def test_file_loading_and_overrides_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    load = getattr(cfg, "load_config", None) or getattr(cfg, "load", None)
    if load is None:
        pytest.skip("load helper not exposed yet")

    base = _get_default_config()
    data = {"run": {"seed": 123}, "plotting": {"style": "dark"}}
    p = tmp_path / "config.json"
    p.write_text(json.dumps(data), encoding="utf-8")

    overrides = {"run": {"seed": 999}, "extra": {"flag": True}}
    c = _call(load, p, base=base, defaults=base, override=overrides, overrides=overrides)
    assert isinstance(c, dict)
    assert c.get("run", {}).get("seed") == 999
    assert c.get("extra", {}).get("flag") is True

    monkeypatch.setenv("EVCONV__RUN__SEED", "111")
    c2 = _call(load, p, base=base, defaults=base)
    assert isinstance(c2, dict)
    assert c2.get("run", {}).get("seed") in (123, 111)
def test_plotting_config_integration():
    c = _get_default_config()
    plotting = c.get("plotting") or c.get("plot") or {}
    assert isinstance(plotting, dict)

    plotting_mod = None
    try:
        from evconv.config import plotting as plotting_mod  # type: ignore
    except Exception:
        plotting_mod = None

    if plotting_mod is None:
        pytest.skip("plotting module not available yet")

    v = getattr(plotting_mod, "validate_plotting_config", None) or getattr(plotting_mod, "validate", None)
    if callable(v):
        out = _call(v, plotting)
        assert out is None or isinstance(out, dict)

    to_kwargs = getattr(plotting_mod, "to_mpl_kwargs", None) or getattr(plotting_mod, "as_mpl_kwargs", None)
    if callable(to_kwargs):
        kw = _call(to_kwargs, plotting)
        assert isinstance(kw, dict)
        assert all(isinstance(k, str) for k in kw.keys())
