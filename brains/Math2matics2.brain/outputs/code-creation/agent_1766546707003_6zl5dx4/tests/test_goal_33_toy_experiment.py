import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def _run(seed: int, out_dir: Path) -> subprocess.CompletedProcess:
    script = Path(__file__).resolve().parents[1] / "src" / "goal_33_toy_experiment.py"
    assert script.is_file(), f"Missing script at {script}"
    env = os.environ.copy()
    # Keep hashing stable for anything that might indirectly rely on it.
    env["PYTHONHASHSEED"] = str(seed)
    cmd = [
        sys.executable,
        str(script),
        "--seed",
        str(seed),
        "--n",
        "200",
        "--noise",
        "0.25",
        "--output-dir",
        str(out_dir),
    ]
    return subprocess.run(cmd, check=True, capture_output=True, text=True, env=env)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
def test_toy_experiment_writes_artifacts_and_is_deterministic(tmp_path: Path) -> None:
    out1 = tmp_path / "run1" / "outputs"
    out2 = tmp_path / "run2" / "outputs"

    _run(seed=123, out_dir=out1)
    _run(seed=123, out_dir=out2)

    res1 = out1 / "results.json"
    fig1 = out1 / "figure.png"
    res2 = out2 / "results.json"
    fig2 = out2 / "figure.png"

    for p in (res1, fig1, res2, fig2):
        assert p.exists(), f"Expected artifact missing: {p}"
        assert p.stat().st_size > 0, f"Expected non-empty artifact: {p}"

    # JSON content must be stable across repeated runs.
    j1 = json.loads(res1.read_text(encoding="utf-8"))
    j2 = json.loads(res2.read_text(encoding="utf-8"))
    assert j1 == j2

    # Also validate raw bytes for both artifacts.
    assert _sha256(res1) == _sha256(res2)
    assert _sha256(fig1) == _sha256(fig2)

    # Light schema checks to ensure results are meaningful.
    assert j1["seed"] == 123
    assert j1["n"] == 200
    assert "metrics" in j1 and set(j1["metrics"]) >= {"mse", "r2"}
    assert "estimated_params" in j1 and set(j1["estimated_params"]) >= {"w", "b"}
