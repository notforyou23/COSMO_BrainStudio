from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


def _run_experiment(repo_root: Path, seed: int, out_rel: Path) -> subprocess.CompletedProcess:
    script = repo_root / "src" / "goal_33_toy_experiment.py"
    if not script.is_file():
        raise AssertionError(f"Missing script: {script}")

    cmd1 = [sys.executable, str(script), "--seed", str(seed), "--output", str(out_rel)]
    p1 = subprocess.run(cmd1, cwd=str(repo_root), capture_output=True, text=True)
    if p1.returncode == 0:
        return p1

    # Fallback if CLI doesn't accept --output
    stderr = (p1.stderr or "") + (p1.stdout or "")
    if "unrecognized arguments" in stderr or "unknown option" in stderr or "No such option" in stderr:
        cmd2 = [sys.executable, str(script), "--seed", str(seed)]
        p2 = subprocess.run(cmd2, cwd=str(repo_root), capture_output=True, text=True)
        return p2

    return p1


def _assert_numbers_are_numeric(obj) -> None:
    if isinstance(obj, dict):
        for v in obj.values():
            _assert_numbers_are_numeric(v)
    elif isinstance(obj, list):
        for v in obj:
            _assert_numbers_are_numeric(v)
    else:
        if isinstance(obj, str):
            assert not re.fullmatch(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", obj), f"Numeric value encoded as string: {obj!r}"


def test_goal_33_toy_experiment_smoke(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    outputs_dir = repo_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    out_rel = Path("outputs") / "goal_33_results.json"
    out_path = repo_root / out_rel
    if out_path.exists():
        out_path.unlink()

    seed = 12345
    proc = _run_experiment(repo_root, seed, out_rel)
    if proc.returncode != 0:
        raise AssertionError(
            "Toy experiment failed.\n"
            f"cmd failed with returncode={proc.returncode}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}\n"
        )

    assert out_path.is_file(), f"Expected artifact not created: {out_path}"
    text = out_path.read_text(encoding="utf-8").strip()
    assert text.startswith("{") and text.endswith("}"), "Artifact should be a JSON object"

    # Stable key order: keys appear in sorted order at top-level.
    pairs = json.loads(text, object_pairs_hook=list)
    top_keys = [k for k, _ in pairs]
    assert top_keys == sorted(top_keys), f"Top-level keys not sorted: {top_keys}"

    data = dict(pairs)
    _assert_numbers_are_numeric(data)

    # If seed is present, it must match.
    if "seed" in data:
        assert data["seed"] == seed, f"Seed mismatch in artifact: {data['seed']} != {seed}"

    # Stable numeric formatting: avoid scientific notation and quoted numerics in raw JSON.
    assert "e+" not in text.lower() and "e-" not in text.lower(), "Avoid scientific notation for stability"
    assert not re.search(r'":\s*"[-+]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"', text), "Numeric values should not be quoted strings"
