from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_RUN = ROOT / "scripts" / "run.py"
OUTPUTS_DIR = ROOT / "outputs"
RUN_STAMP = OUTPUTS_DIR / "run_stamp.json"
RUN_LOG = OUTPUTS_DIR / "run.log"


def _run_entrypoint() -> subprocess.CompletedProcess[str]:
    if not SCRIPTS_RUN.is_file():
        raise AssertionError(f"Missing entrypoint: {SCRIPTS_RUN}")

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    for p in (RUN_STAMP, RUN_LOG):
        if p.exists():
            p.unlink()

    return subprocess.run(
        [sys.executable, str(SCRIPTS_RUN)],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=True,
        env={"PYTHONHASHSEED": "0"},
    )


def test_run_produces_deterministic_artifacts() -> None:
    _run_entrypoint()

    assert RUN_STAMP.is_file(), "outputs/run_stamp.json was not created"
    assert RUN_LOG.is_file(), "outputs/run.log was not created"

    stamp = json.loads(RUN_STAMP.read_text(encoding="utf-8"))
    expected_stamp = {
        "schema_version": 1,
        "project": "generated_script_1766547587041",
        "entrypoint": "scripts/run.py",
        "status": "ok",
        "run_timestamp": "1970-01-01T00:00:00Z",
        "artifacts": {
            "run_stamp": "outputs/run_stamp.json",
            "run_log": "outputs/run.log",
        },
    }
    assert stamp == expected_stamp

    log_text = RUN_LOG.read_text(encoding="utf-8")
    expected_log = (
        "generated_script_1766547587041 run
"
        "schema_version=1
"
        "status=ok
"
    )
    assert log_text == expected_log
