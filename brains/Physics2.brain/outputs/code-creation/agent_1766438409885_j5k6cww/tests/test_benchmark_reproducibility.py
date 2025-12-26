import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def _repo_root() -> Path:
    # tests/ -> repo root
    return Path(__file__).resolve().parents[1]


def _run_benchmark_cli(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    # Ensure `benchmark` package from ./src is importable when running `python -m benchmark.cli`.
    env["PYTHONPATH"] = str(cwd / "src") + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    return subprocess.run(
        [sys.executable, "-m", "benchmark.cli", *args],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_benchmark_case_001_reproduces_expected_json(tmp_path: Path) -> None:
    root = _repo_root()
    expected_path = tmp_path / "benchmark_case_001.expected.json"
    out_path = tmp_path / "benchmark_case_001.out.json"

    # Generate an expected artifact using the library code path.
    # This keeps the test stable even if run from source without packaging.
    from benchmark.reproduce import reproduce, write_json
    from benchmark.json_compare import assert_json_close

    expected = reproduce("benchmark_case_001", seed=0)
    write_json(expected, expected_path)

    # Reproduce via the CLI and verify against the expected JSON file.
    cp = _run_benchmark_cli(
        ["reproduce", "benchmark_case_001", "--seed", "0", "--out", str(out_path), "--expected", str(expected_path)],
        cwd=root,
    )
    assert cp.returncode == 0, f"CLI failed (rc={cp.returncode})\nSTDOUT:\n{cp.stdout}\nSTDERR:\n{cp.stderr}"

    produced = json.loads(out_path.read_text(encoding="utf-8"))
    expected_loaded = json.loads(expected_path.read_text(encoding="utf-8"))
    assert_json_close(produced, expected_loaded, rtol=1e-7, atol=1e-9)
