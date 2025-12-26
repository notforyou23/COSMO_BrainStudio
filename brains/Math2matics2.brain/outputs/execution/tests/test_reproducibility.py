from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonical_json_text(path: Path) -> str:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _run_pipeline(out_dir: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    main_py = repo_root / "src" / "main.py"
    if not main_py.is_file():
        raise FileNotFoundError(f"Expected CLI entrypoint at: {main_py}")

    candidates = [
        [sys.executable, str(main_py), "--output-dir", str(out_dir)],
        [sys.executable, str(main_py), "--output", str(out_dir)],
        [sys.executable, str(main_py), "-o", str(out_dir)],
        [sys.executable, str(main_py), str(out_dir)],
    ]

    last = None
    for cmd in candidates:
        last = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True)
        if last.returncode == 0:
            return

    raise RuntimeError(
        "Pipeline run failed for all known CLI invocations. "
        f"Last cmd: {candidates[-1]}\n"
        f"stdout:\n{last.stdout}\n"
        f"stderr:\n{last.stderr}"
    )


@pytest.mark.parametrize("run_idx", [0, 1])
def test_pipeline_is_reproducible(run_idx: int) -> None:
    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        out1 = Path(d1)
        out2 = Path(d2)

        _run_pipeline(out1)
        _run_pipeline(out2)

        r1, r2 = out1 / "results.json", out2 / "results.json"
        f1, f2 = out1 / "figure.png", out2 / "figure.png"

        assert r1.is_file() and r2.is_file(), "results.json missing from one or both runs"
        assert f1.is_file() and f2.is_file(), "figure.png missing from one or both runs"

        assert _canonical_json_text(r1) == _canonical_json_text(r2), "Canonicalized results.json differs"
        assert _sha256(f1) == _sha256(f2), "figure.png hash differs"
