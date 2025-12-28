import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = ROOT / "runtime" / "_build"
SUMMARY_JSON = BUILD_DIR / "summary.json"


def _rm_build():
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)


def _run_build(extra_args=None, env_overrides=None):
    extra_args = extra_args or []
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    if env_overrides:
        env.update(env_overrides)
    cmd = [sys.executable, "-m", "src.build_runner", *extra_args]
    p = subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
    )
    return p


def _read_summary():
    assert SUMMARY_JSON.exists(), f"Missing summary.json at {SUMMARY_JSON}"
    try:
        return json.loads(SUMMARY_JSON.read_text(encoding="utf-8"))
    except Exception as e:
        raise AssertionError(f"Failed to parse {SUMMARY_JSON}: {e}") from e


def _assert_steps_shape(summary):
    assert isinstance(summary, dict), "summary.json must be a JSON object"
    assert "status" in summary, "summary.json must include 'status'"
    assert "steps" in summary, "summary.json must include 'steps' list"
    assert isinstance(summary["steps"], list), "'steps' must be a list"
    names = [s.get("name") for s in summary["steps"] if isinstance(s, dict)]
    assert names[:3] == ["artifact_gate", "taxonomy_validation", "meta_analysis_demo"], (
        "Expected step order: artifact_gate -> taxonomy_validation -> meta_analysis_demo; "
        f"got {names}"
    )
    return summary["steps"]


def _step_status(steps, name):
    for s in steps:
        if s.get("name") == name:
            return s.get("status")
    return None


@pytest.mark.e2e
def test_build_runner_success_creates_standardized_outputs_and_final_summary():
    _rm_build()
    p = _run_build()
    assert BUILD_DIR.exists(), "Build must standardize outputs under runtime/_build/"
    summary = _read_summary()
    steps = _assert_steps_shape(summary)

    assert p.returncode == 0, f"Expected exit 0, got {p.returncode}. stderr:\n{p.stderr}"
    assert summary["status"] in ("success", "ok"), f"Unexpected final status: {summary.get('status')}"
    assert "summary" in (p.stdout + p.stderr).lower(), "Runner should emit a final summary status"

    for step in ("artifact_gate", "taxonomy_validation", "meta_analysis_demo"):
        assert _step_status(steps, step) in ("success", "ok"), f"Step {step} not successful in summary"
        step_dir = BUILD_DIR / "steps" / step
        assert step_dir.exists(), f"Expected step output dir: {step_dir}"


@pytest.mark.e2e
def test_build_runner_fail_fast_stops_after_taxonomy_failure_and_reports_clearly():
    _rm_build()
    p = _run_build(env_overrides={"COSMO_BUILD_FORCE_FAIL": "taxonomy_validation"})
    assert BUILD_DIR.exists(), "Build must still write outputs under runtime/_build/ on failure"
    summary = _read_summary()
    steps = _assert_steps_shape(summary)

    assert p.returncode != 0, "Expected non-zero exit on forced failure"
    assert summary["status"] in ("failed", "error"), f"Unexpected final status: {summary.get('status')}"
    combined = (p.stdout + p.stderr).lower()
    assert "taxonomy" in combined and ("fail" in combined or "error" in combined), "Expected clear error message"

    assert _step_status(steps, "artifact_gate") in ("success", "ok"), "artifact_gate should have run before failure"
    assert _step_status(steps, "taxonomy_validation") in ("failed", "error"), "taxonomy_validation should be marked failed"
    assert _step_status(steps, "meta_analysis_demo") in ("skipped", "not_run", None), (
        "meta_analysis_demo must not run after taxonomy_validation failure (fail-fast)"
    )

    meta_dir = BUILD_DIR / "steps" / "meta_analysis_demo"
    assert not meta_dir.exists(), "Fail-fast must prevent meta_analysis_demo outputs from being created"
