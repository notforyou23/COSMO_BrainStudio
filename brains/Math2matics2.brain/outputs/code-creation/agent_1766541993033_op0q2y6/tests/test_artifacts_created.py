from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest


def _add_src_to_syspath() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    src = repo_root / "src"
    if src.exists():
        sys.path.insert(0, str(src))


def _run_pipeline() -> None:
    _add_src_to_syspath()
    try:
        import minipipeline  # type: ignore
    except Exception as e:  # pragma: no cover
        raise AssertionError(f"Failed to import minipipeline package: {e}") from e

    # Preferred: public entrypoint in package root.
    if hasattr(minipipeline, "run") and callable(getattr(minipipeline, "run")):
        minipipeline.run()
        return

    # Fallback: run module function.
    try:
        from minipipeline.run import run as run_func  # type: ignore
    except Exception as e:  # pragma: no cover
        raise AssertionError(f"Failed to locate a runnable entrypoint: {e}") from e
    run_func()


@pytest.mark.order(1)
def test_artifacts_created_and_have_expected_content() -> None:
    outputs_dir = Path(os.environ.get("MINIPIPELINE_OUTPUTS_DIR", "/outputs"))
    stamp_path = outputs_dir / "run_stamp.json"
    log_path = outputs_dir / "run.log"

    outputs_dir.mkdir(parents=True, exist_ok=True)
    for p in (stamp_path, log_path):
        if p.exists():
            p.unlink()

    _run_pipeline()

    assert stamp_path.is_file(), f"Missing artifact: {stamp_path}"
    assert log_path.is_file(), f"Missing artifact: {log_path}"

    stamp = json.loads(stamp_path.read_text(encoding="utf-8"))
    assert isinstance(stamp, dict)
    assert stamp.get("schema_version") == 1
    assert stamp.get("run_id") == "deterministic-run"
    assert stamp.get("outputs_dir") == str(outputs_dir)
    assert "payload" in stamp and isinstance(stamp["payload"], dict)
    assert "environment" in stamp and isinstance(stamp["environment"], dict)

    log_text = log_path.read_text(encoding="utf-8")
    assert "RUN_START" in log_text
    assert "RUN_END" in log_text
