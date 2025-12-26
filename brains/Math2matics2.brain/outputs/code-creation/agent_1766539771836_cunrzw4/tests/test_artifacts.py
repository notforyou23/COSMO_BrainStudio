from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REQUIRED_SCHEMA_KEYS = (
    "schema_version",
    "run_id",
    "started_at",
    "finished_at",
    "status",
    "outputs_dir",
    "run_stamp_path",
    "run_log_path",
)


def test_pipeline_emits_expected_artifacts(tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    script_path = project_root / "scripts" / "run_pipeline.py"
    assert script_path.is_file(), f"Missing pipeline script: {script_path}"

    proc = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"Pipeline failed\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"

    outputs_dir = project_root / "outputs"
    run_stamp_path = outputs_dir / "run_stamp.json"
    run_log_path = outputs_dir / "run.log"

    assert outputs_dir.is_dir(), f"Missing outputs dir: {outputs_dir}"
    assert run_stamp_path.is_file(), f"Missing run stamp: {run_stamp_path}"
    assert run_log_path.is_file(), f"Missing run log: {run_log_path}"

    data = json.loads(run_stamp_path.read_text(encoding="utf-8"))
    missing = [k for k in REQUIRED_SCHEMA_KEYS if k not in data]
    assert not missing, f"run_stamp.json missing keys: {missing}"

    assert data["status"] == "success"
    assert isinstance(data["schema_version"], int)
    assert isinstance(data["run_id"], str) and data["run_id"]
    assert isinstance(data["started_at"], str) and data["started_at"]
    assert isinstance(data["finished_at"], str) and data["finished_at"]
