from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


def _project_root() -> Path:
    # tests/ is at project root level in this generated layout
    return Path(__file__).resolve().parents[1]


def _run_toy_experiment(seed: int, cwd: Path) -> None:
    env = os.environ.copy()
    env["PYTHONHASHSEED"] = str(seed)

    # Prefer module invocation; fall back to direct script execution.
    commands = [
        [sys.executable, "-m", "src.goal_33_toy_experiment", "--seed", str(seed)],
        [sys.executable, str(cwd / "src" / "goal_33_toy_experiment.py"), "--seed", str(seed)],
    ]

    last = None
    for cmd in commands:
        try:
            last = subprocess.run(
                cmd,
                cwd=str(cwd),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            continue

        if last.returncode == 0:
            return

    details = ""
    if last is not None:
        details = f"\nSTDOUT:\n{last.stdout}\nSTDERR:\n{last.stderr}"
    raise AssertionError("Toy experiment failed to run successfully." + details)


def _canonical_json_text(obj) -> str:
    # Stable keys and stable whitespace; newline-terminated artifact.
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def test_goal_33_toy_experiment_smoke_seeded_results_artifact():
    root = _project_root()
    outputs_dir = root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    artifact = outputs_dir / "goal_33_results.json"

    if artifact.exists():
        artifact.unlink()

    _run_toy_experiment(seed=123, cwd=root)

    assert artifact.exists(), f"Missing results artifact: {artifact}"
    raw = artifact.read_text(encoding="utf-8")

    # Must be valid JSON.
    data = json.loads(raw)

    # Must be stable-key, stable-format JSON (canonical dump matches exactly).
    assert raw == _canonical_json_text(data), "Results JSON is not in canonical stable format."

    # Extra guardrail: avoid scientific notation for determinism across readers.
    assert not re.search(r"[eE][+-]?\d+", raw), "Results JSON contains scientific-notation numbers."
