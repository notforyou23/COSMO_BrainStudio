import importlib
import inspect
import logging
import os
import re
from pathlib import Path

import pytest


_ROOT_OUTPUTS_RE = re.compile(r'(?<![A-Za-z0-9_])/outputs(?=/|$)')


def _has_root_outputs(text: str) -> bool:
    return bool(_ROOT_OUTPUTS_RE.search(text or ""))


def _file_has_root_outputs(p: Path) -> bool:
    try:
        data = p.read_bytes()
    except Exception:
        return False
    try:
        s = data.decode("utf-8", errors="ignore")
        return _has_root_outputs(s)
    except Exception:
        return _has_root_outputs(repr(data))


def _safe_import(module: str):
    try:
        return importlib.import_module(module)
    except Exception:
        return None


def _try_call(func, base_dir: Path):
    sig = None
    try:
        sig = inspect.signature(func)
    except Exception:
        return False

    kwargs = {}
    args = []
    for name, param in sig.parameters.items():
        if name in ("self", "cls"):
            continue
        if name in ("output_dir", "out_dir", "outputs_dir", "base_dir", "root", "dest_dir"):
            kwargs[name] = base_dir
            continue
        if name in ("path", "dst", "dest", "file_path", "output_path", "artifact_path"):
            kwargs[name] = base_dir / "artifact.txt"
            continue
        if name in ("rel_path", "name", "filename", "artifact_name"):
            kwargs[name] = "artifact.txt"
            continue
        if name in ("text", "content", "message", "log_text"):
            kwargs[name] = "hello"
            continue
        if name in ("data", "obj", "payload", "record", "records"):
            kwargs[name] = {"ok": True}
            continue
        if name in ("logger", "log"):
            kwargs[name] = logging.getLogger("test_no_absolute_outputs_paths")
            continue
        if param.default is not inspect._empty:
            continue
        return False

    try:
        func(*args, **kwargs)
        return True
    except TypeError:
        return False
    except Exception:
        return True


def _invoke_key_paths(base_dir: Path):
    called = 0

    writers = _safe_import("src.io.writers")
    if writers:
        for name in ("write_text", "write_json", "write_log", "write_artifact", "write_metrics"):
            f = getattr(writers, name, None)
            if callable(f):
                if _try_call(f, base_dir):
                    called += 1
        if called == 0:
            for n, f in vars(writers).items():
                if callable(f) and n.startswith("write"):
                    if _try_call(f, base_dir):
                        called += 1
                        if called >= 3:
                            break

    rp = _safe_import("scripts.run_pipeline")
    if rp:
        for name in ("main", "run", "run_pipeline"):
            f = getattr(rp, name, None)
            if callable(f):
                try:
                    sig = inspect.signature(f)
                except Exception:
                    sig = None
                try:
                    if sig and len(sig.parameters) == 0:
                        f()
                    else:
                        kwargs = {}
                        if sig:
                            for pn, param in sig.parameters.items():
                                if pn in ("argv", "args"):
                                    kwargs[pn] = []
                                elif pn in ("output_dir", "out_dir", "outputs_dir", "base_dir"):
                                    kwargs[pn] = base_dir
                                elif param.default is inspect._empty:
                                    raise TypeError("unsupported signature")
                        f(**kwargs)
                    called += 1
                    break
                except Exception:
                    called += 1
                    break

    return called


@pytest.mark.filterwarnings("ignore")
def test_no_absolute_outputs_paths_in_logs_or_artifacts(tmp_path, monkeypatch, capsys, caplog):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "out"))
    monkeypatch.setenv("OUTPUTS_DIR", str(tmp_path / "out"))
    monkeypatch.setenv("OUT_DIR", str(tmp_path / "out"))

    caplog.set_level(logging.INFO)

    called = _invoke_key_paths(tmp_path)

    out = capsys.readouterr()
    combined_logs = (caplog.text or "") + "\n" + (out.out or "") + "\n" + (out.err or "")

    assert not _has_root_outputs(combined_logs), "Found root-level /outputs path in captured logs/stdout/stderr"

    paths_to_scan = []
    for base in {tmp_path, tmp_path / "out", tmp_path / "outputs"}:
        if base.exists():
            paths_to_scan.extend([p for p in base.rglob("*") if p.is_file()])

    for p in paths_to_scan:
        assert not _file_has_root_outputs(p), f"Found root-level /outputs path inside artifact: {p}"

    if called == 0:
        pytest.skip("No known writer/pipeline entrypoints available to execute in this project layout")
