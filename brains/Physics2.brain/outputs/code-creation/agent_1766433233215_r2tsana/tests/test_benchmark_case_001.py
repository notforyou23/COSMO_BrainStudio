import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _find_file(patterns):
    root = _repo_root()
    for pat in patterns:
        hits = list(root.rglob(pat))
        if hits:
            return sorted(hits)[0]
    return None


def _find_expected_files():
    root = _repo_root()
    cands = sorted(
        p for p in root.rglob("*.json")
        if re.search(r"benchmark_case_001.*expected", p.name)
    )
    if cands:
        return cands
    # fallback: dedicated expected directory
    expected_dir = _find_file(["**/expected/**/benchmark_case_001*.json", "**/expected*benchmark_case_001*.json"])
    return [expected_dir] if expected_dir else []


def _find_input_file():
    return _find_file([
        "**/examples/**/benchmark_case_001*.json",
        "**/example/**/benchmark_case_001*.json",
        "**/inputs/**/benchmark_case_001*.json",
        "**/benchmark_case_001*.json",
    ])
def _json_load(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _compare(a, b, *, atol=1e-6, rtol=1e-6, path="root"):
    if _is_number(a) and _is_number(b):
        diff = abs(a - b)
        tol = atol + rtol * abs(b)
        if diff <= tol:
            return
        raise AssertionError(f"{path}: {a} != {b} (diff={diff}, tol={tol})")
    if type(a) != type(b):
        raise AssertionError(f"{path}: type {type(a).__name__} != {type(b).__name__}")
    if isinstance(a, dict):
        if set(a) != set(b):
            missing = sorted(set(b) - set(a))
            extra = sorted(set(a) - set(b))
            raise AssertionError(f"{path}: key mismatch missing={missing} extra={extra}")
        for k in a:
            _compare(a[k], b[k], atol=atol, rtol=rtol, path=f"{path}.{k}")
        return
    if isinstance(a, list):
        if len(a) != len(b):
            raise AssertionError(f"{path}: len {len(a)} != {len(b)}")
        for i, (ai, bi) in enumerate(zip(a, b)):
            _compare(ai, bi, atol=atol, rtol=rtol, path=f"{path}[{i}]")
        return
    if a != b:
        raise AssertionError(f"{path}: {a!r} != {b!r}")
def _run_reference(input_path: Path, output_dir: Path):
    root = _repo_root()

    # Prefer an explicit CLI module if present; fall back to a generated_script_*.py.
    script = _find_file(["generated_script_*.py", "src/**/main.py", "main.py", "run.py"])
    if script is None:
        raise FileNotFoundError("Could not locate reference implementation script (e.g., generated_script_*.py).")

    cmd = [sys.executable, str(script), "--input", str(input_path), "--output", str(output_dir)]
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    proc = subprocess.run(cmd, cwd=str(root), env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            "Reference run failed.\n"
            f"CMD: {' '.join(cmd)}\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
@pytest.mark.benchmark
def test_benchmark_case_001_reference_matches_expected():
    input_path = _find_input_file()
    if input_path is None:
        pytest.skip("benchmark_case_001 input JSON not found in repository.")

    expected_files = _find_expected_files()
    if not expected_files:
        pytest.skip("benchmark_case_001 expected output JSON not found in repository.")

    out_dir = _repo_root() / "tests" / "ci_outputs" / "benchmark_case_001"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    _run_reference(input_path, out_dir)

    produced = sorted(out_dir.rglob("*.json"))
    assert produced, f"No JSON outputs produced under {out_dir}"

    if len(expected_files) == 1 and len(produced) == 1:
        exp, act = expected_files[0], produced[0]
        _compare(_json_load(act), _json_load(exp), atol=1e-6, rtol=1e-6)
        return

    produced_by_name = {p.name: p for p in produced}
    for exp in expected_files:
        # Match either exact name or name with '_expected' removed.
        act = produced_by_name.get(exp.name)
        if act is None:
            alt = re.sub(r"(_|-)?expected", "", exp.name, flags=re.IGNORECASE)
            act = produced_by_name.get(alt)
        assert act is not None, f"Missing produced output for expected file {exp.name}"
        _compare(_json_load(act), _json_load(exp), atol=1e-6, rtol=1e-6)
