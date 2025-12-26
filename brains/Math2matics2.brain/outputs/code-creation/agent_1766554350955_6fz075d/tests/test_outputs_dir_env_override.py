import importlib
import inspect
import os
import sys
from pathlib import Path

import pytest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _import_outputs_dir_module():
    # Prefer package import if src is a package; else allow direct path loading.
    root = _repo_root()
    src_dir = root / "src"
    if not src_dir.exists():
        raise AssertionError(f"Expected src directory at {src_dir}")

    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    try:
        return importlib.import_module("src.utils.outputs_dir")
    except Exception as e:
        raise AssertionError(f"Could not import src.utils.outputs_dir: {e}") from e


def _get_outputs_dir_callable(mod):
    for name in ("get_outputs_dir", "resolve_outputs_dir", "outputs_dir"):
        fn = getattr(mod, name, None)
        if callable(fn):
            return fn
    raise AssertionError("No outputs dir resolver callable found in src.utils.outputs_dir")


def _candidate_writer_modules():
    # Common locations/names for artifact writers in generated repos.
    return (
        "src.utils.artifact_writers",
        "src.utils.artifacts",
        "src.utils.writers",
        "src.artifacts",
        "src.writers",
    )


def _iter_public_callables(mod):
    for name in dir(mod):
        if name.startswith("_"):
            continue
        obj = getattr(mod, name, None)
        if callable(obj):
            yield name, obj


def _looks_like_writer(name: str) -> bool:
    n = name.lower()
    return any(k in n for k in ("write", "save", "emit", "artifact", "report"))


def _call_writer_with_heuristics(fn, outputs_dir: Path, filename: str) -> bool:
    sig = None
    try:
        sig = inspect.signature(fn)
    except Exception:
        sig = None

    json_obj = {"hello": "world"}
    text = "hello world"

    # Try a few direct common patterns first.
    direct_attempts = [
        ((), {"filename": filename, "data": json_obj}),
        ((), {"file_name": filename, "data": json_obj}),
        ((), {"path": filename, "data": json_obj}),
        ((json_obj, filename), {}),
        ((filename, json_obj), {}),
        ((text, filename), {}),
        ((filename, text), {}),
    ]
    for args, kwargs in direct_attempts:
        try:
            rv = fn(*args, **kwargs)
            _assert_written(outputs_dir, rv)
            return True
        except TypeError:
            continue
        except Exception:
            # If it ran but didn't write, let it fall through to other attempts.
            continue

    # Signature-based binding.
    if sig is not None:
        params = list(sig.parameters.values())
        args = []
        kwargs = {}
        for p in params:
            if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
                continue
            pn = p.name.lower()
            if pn in ("outputs_dir", "output_dir", "out_dir", "base_dir", "root_dir", "directory", "dir"):
                kwargs[p.name] = outputs_dir
            elif "file" in pn or "path" in pn or "name" in pn:
                kwargs[p.name] = filename
            elif pn in ("data", "obj", "payload", "content", "text", "value"):
                kwargs[p.name] = json_obj if pn in ("data", "obj", "payload", "value") else text

        try:
            rv = fn(*args, **kwargs)
            _assert_written(outputs_dir, rv)
            return True
        except Exception:
            return False

    return False


def _assert_written(outputs_dir: Path, rv):
    outputs_dir = Path(outputs_dir)
    # Prefer checking return value if it looks like a path.
    if isinstance(rv, (str, Path)):
        p = Path(rv)
        if not p.is_absolute():
            p = outputs_dir / p
        if p.exists() and p.is_file():
            return
    # Otherwise, ensure some file exists in outputs_dir.
    files = [p for p in outputs_dir.rglob("*") if p.is_file()]
    if not files:
        raise AssertionError(f"No files were written under outputs_dir={outputs_dir}")


@pytest.mark.parametrize("module_name", _candidate_writer_modules())
def test_outputs_dir_env_override_end_to_end(tmp_path, monkeypatch, module_name):
    out = tmp_path / "my_outputs"
    monkeypatch.setenv("OUTPUTS_DIR", str(out))

    # Ensure resolver respects env var and creates directory.
    od_mod = _import_outputs_dir_module()
    importlib.reload(od_mod)
    get_out = _get_outputs_dir_callable(od_mod)
    resolved = Path(get_out())
    assert resolved == out
    assert resolved.exists() and resolved.is_dir()

    # Invoke a writer and ensure it writes into OUTPUTS_DIR.
    try:
        writer_mod = importlib.import_module(module_name)
    except Exception:
        pytest.skip(f"Writer module not importable: {module_name}")

    filename = "outputs_dir_env_override_test_artifact.json"
    wrote = False
    for name, fn in _iter_public_callables(writer_mod):
        if not _looks_like_writer(name):
            continue
        if _call_writer_with_heuristics(fn, out, filename):
            wrote = True
            break

    if not wrote:
        raise AssertionError(
            f"No compatible artifact writer callable found in {module_name}; "
            "expected at least one writer to accept content and a filename/path."
        )

    assert any(p.is_file() for p in out.rglob("*"))
