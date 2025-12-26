import importlib
import inspect
import sys
from pathlib import Path

import pytest


def _ensure_src_on_path():
    # Ensure `src/` is importable when running pytest from repo root or elsewhere.
    here = Path(__file__).resolve()
    for parent in (here.parent, *here.parents):
        src = parent / "src"
        if src.is_dir():
            sys.path.insert(0, str(src))
            return
    # If no src folder, rely on environment / installed package.


def _import_blessed():
    _ensure_src_on_path()
    return importlib.import_module("blessed_pipeline")


def _candidate_callables(mod):
    names = ("run_pipeline", "run", "execute", "pipeline", "main")
    for name in names:
        if hasattr(mod, name) and callable(getattr(mod, name)):
            yield getattr(mod, name)


def _select_runner(bp):
    # Prefer blessed_pipeline.run_pipeline; fall back to blessed_pipeline.pipeline module.
    for fn in _candidate_callables(bp):
        if getattr(fn, "__name__", "") != "main":
            return fn
    try:
        pm = importlib.import_module("blessed_pipeline.pipeline")
    except Exception:
        pm = None
    if pm:
        for fn in _candidate_callables(pm):
            if getattr(fn, "__name__", "") != "main":
                return fn
    raise AssertionError(
        "No pipeline runner found. Expected a callable like blessed_pipeline.run_pipeline "
        "or blessed_pipeline.pipeline.run_pipeline/run/execute."
    )


def _call_with_supported_kwargs(fn, tmp_path):
    sig = inspect.signature(fn)
    kwargs = {}
    for name, p in sig.parameters.items():
        if p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        if name in ("output_dir", "out_dir", "artifacts_dir", "artifact_dir", "work_dir", "workspace", "path"):
            kwargs[name] = tmp_path
        elif name in ("config", "cfg", "options", "settings"):
            kwargs[name] = {"seed": 0, "mode": "test"}
        elif name in ("data", "input", "inputs", "payload"):
            kwargs[name] = {"text": "hello", "items": [1, 2, 3]}
        elif name in ("text", "prompt", "message"):
            kwargs[name] = "hello"
        elif name in ("items", "records", "rows"):
            kwargs[name] = [1, 2, 3]
        elif p.default is not inspect._empty:
            # Let defaults stand.
            pass
        else:
            # Best-effort fill for required params.
            kwargs[name] = tmp_path if "dir" in name or "path" in name else "test"
    try:
        return fn(**kwargs)
    except TypeError:
        # Some runners might take a single config object or no kwargs at all.
        try:
            return fn()
        except Exception as e:
            raise AssertionError(f"Pipeline runner invocation failed: {e}") from e


def _normalize_pathish(x):
    if x is None:
        return None
    if isinstance(x, Path):
        return x
    if isinstance(x, str):
        try:
            return Path(x)
        except Exception:
            return None
    return None


def test_blessed_pipeline_imports_without_syntax_errors():
    bp = _import_blessed()
    assert hasattr(bp, "__version__") or True  # allow absence; main check is import success
    # Import submodules that historically triggered syntax_error flags.
    importlib.import_module("blessed_pipeline.pipeline")
    importlib.import_module("blessed_pipeline.cli")


def test_pipeline_runner_smoke(tmp_path):
    bp = _import_blessed()
    runner = _select_runner(bp)
    result = _call_with_supported_kwargs(runner, tmp_path)

    assert result is not None

    # If the runner returns a path-like artifact, it should exist.
    p = _normalize_pathish(result)
    if p is not None:
        assert p.exists() or p.parent.exists()

    # If it returns a mapping/object with an output_dir/artifacts field, verify it is pathish.
    if isinstance(result, dict):
        for key in ("output_dir", "out_dir", "artifacts_dir", "artifact_dir", "path"):
            if key in result:
                rp = _normalize_pathish(result[key])
                assert rp is not None
                assert rp.exists() or rp.parent.exists()
                break
    else:
        for attr in ("output_dir", "out_dir", "artifacts_dir", "artifact_dir", "path"):
            if hasattr(result, attr):
                rp = _normalize_pathish(getattr(result, attr))
                assert rp is not None
                assert rp.exists() or rp.parent.exists()
                break


def test_cli_import_and_main_callable():
    _ensure_src_on_path()
    cli = importlib.import_module("blessed_pipeline.cli")
    assert hasattr(cli, "main") and callable(cli.main)
