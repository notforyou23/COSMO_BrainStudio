from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    # tests/ -> repo root
    return Path(__file__).resolve().parents[1]


def test_pipeline_writes_artifacts():
    root = _repo_root()
    script = root / "scripts" / "run_pipeline.py"
    assert script.exists(), f"Missing entrypoint: {script}"

    outputs_dir = root / "outputs"
    stamp_path = outputs_dir / "run_stamp.json"
    log_path = outputs_dir / "run.log"

    # Ensure we validate fresh-ish artifacts without being overly destructive.
    stamp_path.unlink(missing_ok=True)
    log_path.unlink(missing_ok=True)

    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")

    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"Pipeline failed. stdout:\n{proc.stdout}\n\nstderr:\n{proc.stderr}"

    assert outputs_dir.exists() and outputs_dir.is_dir(), "outputs/ directory was not created"
    assert stamp_path.exists() and stamp_path.is_file(), "outputs/run_stamp.json was not created"
    assert log_path.exists() and log_path.is_file(), "outputs/run.log was not created"
    assert log_path.stat().st_size > 0, "outputs/run.log is empty"

    data = json.loads(stamp_path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "run_stamp.json must contain a JSON object"

    expected_keys = {"run_id", "status", "started_at"}
    missing = sorted(expected_keys - set(data.keys()))
    assert not missing, f"run_stamp.json missing required keys: {missing}. Present keys: {sorted(data.keys())}"
