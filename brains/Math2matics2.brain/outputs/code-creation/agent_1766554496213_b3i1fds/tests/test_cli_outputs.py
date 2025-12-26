import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


def _sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def _sha256_path(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run_cli(root: Path) -> None:
    run_py = root / "src" / "run.py"
    if not run_py.is_file():
        raise AssertionError(f"Missing CLI entrypoint: {run_py}")
    env = os.environ.copy()
    env.setdefault("PYTHONHASHSEED", "0")
    subprocess.run([sys.executable, str(run_py)], cwd=str(root), env=env, check=True)


def _read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def _assert_results_schema(obj: dict) -> None:
    assert isinstance(obj, dict)
    for k in ("schema_version", "seed", "metrics"):
        assert k in obj
    assert isinstance(obj["schema_version"], int)
    assert isinstance(obj["seed"], int)
    assert isinstance(obj["metrics"], dict)
    assert all(isinstance(k, str) for k in obj["metrics"].keys())
    assert all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in obj["metrics"].values())


def _assert_hashes_schema(obj: dict) -> None:
    assert isinstance(obj, dict)
    for k in ("results.json", "figure.png"):
        assert k in obj
        assert isinstance(obj[k], str)
        assert re.fullmatch(r"[0-9a-f]{64}", obj[k]) is not None


def test_cli_outputs_deterministic(tmp_path: Path) -> None:
    root = _repo_root()
    outputs = root / "outputs"
    if outputs.exists():
        shutil.rmtree(outputs)
    outputs.mkdir(parents=True, exist_ok=True)

    _run_cli(root)

    results_p = outputs / "results.json"
    fig_p = outputs / "figure.png"
    hashes_p = outputs / "hashes.json"

    assert results_p.is_file()
    assert fig_p.is_file()
    assert hashes_p.is_file()

    results1_bytes = results_p.read_bytes()
    fig1_bytes = fig_p.read_bytes()
    hashes1 = _read_json(hashes_p)
    results1 = _read_json(results_p)

    _assert_results_schema(results1)
    _assert_hashes_schema(hashes1)

    assert hashes1["results.json"] == _sha256_bytes(results1_bytes)
    assert hashes1["figure.png"] == _sha256_bytes(fig1_bytes)

    shutil.rmtree(outputs)
    outputs.mkdir(parents=True, exist_ok=True)

    _run_cli(root)

    results2_bytes = results_p.read_bytes()
    fig2_bytes = fig_p.read_bytes()
    hashes2 = _read_json(hashes_p)
    results2 = _read_json(results_p)

    _assert_results_schema(results2)
    _assert_hashes_schema(hashes2)

    assert hashes2["results.json"] == _sha256_bytes(results2_bytes)
    assert hashes2["figure.png"] == _sha256_bytes(fig2_bytes)

    assert results2_bytes == results1_bytes
    assert fig2_bytes == fig1_bytes
    assert hashes2 == hashes1
