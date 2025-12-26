import json
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
REPORT_JSON = OUTPUTS_DIR / "report.json"


def run_pipeline() -> subprocess.CompletedProcess:
    if OUTPUTS_DIR.exists():
        shutil.rmtree(OUTPUTS_DIR)
    proc = subprocess.run(
        [sys.executable, "-m", "minipipe.run"],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(
            "Pipeline failed (non-zero exit).
"
            f"returncode={proc.returncode}
"
            f"stdout:\n{proc.stdout}
"
            f"stderr:\n{proc.stderr}
"
        )
    return proc


def _assert_required_keys(obj: dict, required: set[str]) -> None:
    missing = sorted(required - set(obj.keys()))
    assert not missing, f"Missing required report.json keys: {missing}. Present: {sorted(obj.keys())}"


def test_pipeline_creates_outputs_and_report_json():
    run_pipeline()
    assert OUTPUTS_DIR.exists() and OUTPUTS_DIR.is_dir(), "outputs/ directory was not created"
    assert REPORT_JSON.exists() and REPORT_JSON.is_file(), "outputs/report.json was not created"
    data = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "report.json must be a JSON object"
    _assert_required_keys(data, {"status", "artifacts"})
    assert data["status"] in {"ok", "success", "done", "completed"}, f"Unexpected status: {data['status']!r}"


def test_report_artifacts_exist_when_paths_provided():
    run_pipeline()
    data = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    artifacts = data.get("artifacts")
    assert artifacts is not None, "report.json must contain an 'artifacts' key"

    paths = []
    if isinstance(artifacts, dict):
        for v in artifacts.values():
            if isinstance(v, str):
                paths.append(v)
            elif isinstance(v, (list, tuple)):
                paths.extend([p for p in v if isinstance(p, str)])
    elif isinstance(artifacts, list):
        paths.extend([p for p in artifacts if isinstance(p, str)])

    # If the pipeline reports artifact paths, ensure those files exist.
    for rel in paths:
        p = Path(rel)
        artifact_path = p if p.is_absolute() else (PROJECT_ROOT / p)
        if not artifact_path.exists():
            # Common convention: paths in report.json are relative to outputs/
            alt = OUTPUTS_DIR / rel
            assert alt.exists(), f"Reported artifact does not exist: {rel} (checked {artifact_path} and {alt})"
