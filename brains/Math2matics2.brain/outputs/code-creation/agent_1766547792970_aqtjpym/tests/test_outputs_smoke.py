from __future__ import annotations

import inspect
import os
import shutil
from importlib import import_module
from pathlib import Path

import pytest
def _repo_root() -> Path:
    # tests/ is expected to live under the repo root
    return Path(__file__).resolve().parents[1]
def _clear_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    # Keep this list broad to avoid accidentally inheriting an override from CI/dev shells
    for key in (
        "OUTPUT_DIR",
        "OUTPUT_PATH",
        "OUTPUTS_DIR",
        "OUTPUTS_PATH",
        "PIPELINE_OUTPUT_DIR",
        "PIPELINE_OUTPUT_PATH",
        "COSMO_OUTPUT_DIR",
        "COSMO_OUTPUT_PATH",
    ):
        monkeypatch.delenv(key, raising=False)
def _resolve_outputs_dir(repo_root: Path) -> Path:
    # Canonical resolver is expected to live here; test dynamically locates the callable.
    mod = import_module("src.output_paths")

    candidates = []
    for name in ("get_output_dir", "get_outputs_dir", "resolve_output_dir", "outputs_dir", "output_dir"):
        fn = getattr(mod, name, None)
        if callable(fn):
            candidates.append(fn)

    if not candidates:
        for _, fn in vars(mod).items():
            if callable(fn):
                candidates.append(fn)

    last_err = None
    for fn in candidates:
        try:
            sig = inspect.signature(fn)
            params = list(sig.parameters.values())
            if len(params) == 0:
                out = fn()
            elif len(params) == 1:
                out = fn(repo_root)
            else:
                continue
            p = Path(out)
            return p
        except Exception as e:  # pragma: no cover
            last_err = e
            continue

    raise AssertionError(f"Could not call an outputs-dir resolver from src.output_paths (last_err={last_err!r})")
def test_outputs_created_in_repo_relative_outputs_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = _repo_root()
    monkeypatch.chdir(repo_root)
    _clear_env_overrides(monkeypatch)

    expected = (repo_root / "outputs").resolve()

    # Start clean to make the assertion meaningful and avoid stale artifacts.
    if expected.exists():
        shutil.rmtree(expected)

    out_dir = _resolve_outputs_dir(repo_root).resolve()

    assert out_dir == expected, f"Expected outputs dir {expected} but got {out_dir}"
    assert out_dir.is_dir(), "Outputs directory should be created by the resolver"
    assert str(out_dir) != "/outputs", "Pipeline must not hardcode absolute /outputs"
    assert out_dir.is_absolute() and str(out_dir).startswith(str(repo_root.resolve())), "Outputs must be repo-relative by default"

    # Smoke artifact: ensure the directory is writable and stays under the canonical location.
    smoke = out_dir / "smoke_test_artifact.txt"
    smoke.write_text("ok\n", encoding="utf-8")
    assert smoke.exists()
    assert smoke.resolve().is_file()
    assert str(smoke.resolve()).startswith(str(expected))
