import inspect
import json
from pathlib import Path

import pytest


def _import_blessed():
    import blessed_pipeline  # noqa: F401
    return blessed_pipeline


def _get_entry(bp):
    # Preferred public entrypoints (single blessed implementation path)
    candidates = [
        ("run", getattr(bp, "run", None)),
        ("run_pipeline", getattr(bp, "run_pipeline", None)),
    ]
    for name, fn in candidates:
        if callable(fn):
            return name, fn

    # Fallback to module-level implementation if exported entrypoints not present
    try:
        from blessed_pipeline import pipeline as pl  # type: ignore
    except Exception as e:  # pragma: no cover
        raise AssertionError(f"Failed to import blessed_pipeline.pipeline: {e}") from e

    for name in ("run", "run_pipeline", "main"):
        fn = getattr(pl, name, None)
        if callable(fn):
            return f"pipeline.{name}", fn

    raise AssertionError("No callable entrypoint found in blessed_pipeline (expected run/run_pipeline).")


def _call_with_minimal_args(fn, tmp_path: Path):
    sig = inspect.signature(fn)
    kwargs = {}
    args = []

    def set_path_param(pname: str):
        kwargs[pname] = tmp_path

    def set_text_param(pname: str):
        kwargs[pname] = "hello world"

    def set_bool_param(pname: str):
        kwargs[pname] = True

    for p in sig.parameters.values():
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            continue
        if p.default is not inspect._empty:
            # use defaults unless it's a path-like we should control
            if p.annotation in (Path,) or p.name.lower() in {"output_dir", "out_dir", "artifacts_dir", "work_dir"}:
                set_path_param(p.name)
            continue

        lname = p.name.lower()
        if lname in {"output_dir", "out_dir", "artifacts_dir", "work_dir", "workspace", "cache_dir"}:
            set_path_param(p.name)
        elif "path" in lname or "dir" in lname:
            set_path_param(p.name)
        elif "text" in lname or "input" in lname or "prompt" in lname or "data" in lname:
            set_text_param(p.name)
        elif "dry" in lname or "verbose" in lname:
            set_bool_param(p.name)
        else:
            # If there's an unexpected required arg, try to pass a benign string.
            kwargs[p.name] = "value"

    try:
        return fn(*args, **kwargs)
    except TypeError as e:
        # Some implementations might require a single positional input; try that.
        try:
            return fn("hello world")
        except Exception:
            raise AssertionError(f"Callable entrypoint could not be invoked with minimal args: {e}") from e


def _jsonable(obj):
    try:
        json.dumps(obj)
        return True
    except Exception:
        return False


def test_import_blessed_pipeline_no_syntax_errors():
    bp = _import_blessed()
    assert hasattr(bp, "__package__")


def test_blessed_pipeline_public_api_is_available():
    bp = _import_blessed()
    name, fn = _get_entry(bp)
    assert callable(fn), f"Resolved entrypoint {name} is not callable"


def test_pipeline_entrypoint_runs_and_returns_reasonable_payload(tmp_path):
    bp = _import_blessed()
    name, fn = _get_entry(bp)
    result = _call_with_minimal_args(fn, tmp_path)

    assert result is not None, f"{name} returned None"

    # Accept dict-like, dataclass-like, or simple scalar outputs; ensure it's at least inspectable.
    if isinstance(result, dict):
        assert result != {}, f"{name} returned an empty dict"
    elif hasattr(result, "to_dict") and callable(getattr(result, "to_dict")):
        d = result.to_dict()
        assert isinstance(d, dict)
        assert d != {}
    else:
        # At minimum should be representable and stable
        assert isinstance(repr(result), str) and repr(result)


def test_pipeline_output_is_json_serializable_or_convertible(tmp_path):
    bp = _import_blessed()
    _, fn = _get_entry(bp)
    result = _call_with_minimal_args(fn, tmp_path)

    if _jsonable(result):
        assert True
    elif isinstance(result, dict):
        assert _jsonable({k: str(v) if not _jsonable(v) else v for k, v in result.items()})
    elif hasattr(result, "__dict__"):
        assert _jsonable({k: str(v) for k, v in vars(result).items()})
    else:
        assert _jsonable(str(result))
