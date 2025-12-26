import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
RUN_LOG = OUTPUTS / "run.log"
RUNNER = ROOT / "scripts" / "run_pipeline.py"


def _clean_outputs():
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    for p in OUTPUTS.iterdir():
        if p.name == ".gitkeep":
            continue
        if p.is_file() or p.is_symlink():
            p.unlink(missing_ok=True)
        elif p.is_dir():
            for sub in sorted(p.rglob("*"), reverse=True):
                if sub.is_file() or sub.is_symlink():
                    sub.unlink(missing_ok=True)
                elif sub.is_dir():
                    sub.rmdir()
            p.rmdir()


def _run_pipeline():
    assert RUNNER.exists(), f"Missing entrypoint runner: {RUNNER}"
    env = os.environ.copy()
    env.setdefault("PIPELINE_MODE", "lightweight")
    env.setdefault("LIGHTWEIGHT", "1")
    env.setdefault("CI", env.get("CI", "1"))

    candidates = [
        [sys.executable, str(RUNNER), "--lightweight"],
        [sys.executable, str(RUNNER), "--mode", "lightweight"],
        [sys.executable, str(RUNNER)],
    ]

    last = None
    for cmd in candidates:
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(ROOT),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300,
            )
            if proc.returncode == 0:
                return proc
            last = proc
        except subprocess.TimeoutExpired as e:
            raise AssertionError(f"Pipeline timed out running: {' '.join(cmd)}") from e

    msg = ""
    if last is not None:
        msg = f"\nSTDOUT:\n{last.stdout[-2000:]}\nSTDERR:\n{last.stderr[-2000:]}"
    raise AssertionError("Pipeline runner failed for all candidate commands." + msg)


def _list_artifacts():
    if not OUTPUTS.exists():
        return []
    artifacts = []
    for p in OUTPUTS.iterdir():
        if p.name in {".gitkeep"}:
            continue
        if p.is_file():
            artifacts.append(p)
    return sorted(artifacts)


def test_pipeline_runnable_lightweight_creates_log_and_artifacts():
    _clean_outputs()
    proc = _run_pipeline()

    assert RUN_LOG.exists(), "Expected outputs/run.log to be created by the pipeline."
    assert RUN_LOG.stat().st_size > 0, "outputs/run.log exists but is empty."

    artifacts = [p for p in _list_artifacts() if p.name != "run.log"]
    assert artifacts, "Expected at least one output artifact besides outputs/run.log."

    for p in artifacts:
        assert p.stat().st_size > 0, f"Artifact is empty: {p.name}"
        if p.suffix.lower() == ".json":
            try:
                obj = json.loads(p.read_text(encoding="utf-8"))
            except Exception as e:
                raise AssertionError(f"Invalid JSON artifact: {p.name}") from e
            assert isinstance(obj, (dict, list)), f"JSON artifact should be dict/list: {p.name}"

    assert proc.returncode == 0
