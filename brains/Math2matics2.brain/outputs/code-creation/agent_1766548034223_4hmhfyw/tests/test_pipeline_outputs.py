from __future__ import annotations
import os
os.chdir(r'/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution')


import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
REQUIRED = ["run_stamp.json", "run.log", "results.json", "figure.png"]


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _run_pipeline() -> None:
    env = os.environ.copy()
    env.setdefault("PYTHONHASHSEED", "0")
    candidates = [
        [sys.executable, str(ROOT / "scripts" / "run.py")],
        [sys.executable, "-m", "scripts.run"],
    ]
    last = None
    for cmd in candidates:
        try:
            last = subprocess.run(
                cmd, cwd=str(ROOT), env=env, capture_output=True, text=True, check=False
            )
        except FileNotFoundError:
            continue
        if last.returncode == 0:
            return
    msg = "Pipeline command failed.\n"
    if last is not None:
        msg += f"cmd={last.args}\nrc={last.returncode}\nstdout={last.stdout}\nstderr={last.stderr}\n"
    raise AssertionError(msg)


def _clean_outputs_dir() -> None:
    if not OUTPUTS.exists():
        return
    for p in OUTPUTS.rglob("*"):
        if p.is_file():
            p.unlink()
    for p in sorted(OUTPUTS.rglob("*"), key=lambda x: len(x.parts), reverse=True):
        if p.is_dir():
            try:
                p.rmdir()
            except OSError:
                pass


def _load_json(p: Path) -> dict:
    data = json.loads(p.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{p.name} must be a JSON object"
    assert data, f"{p.name} must not be empty"
    def _walk(v):
        if v is None or isinstance(v, (bool, int, float, str)):
            return
        if isinstance(v, list):
            for x in v:
                _walk(x)
            return
        if isinstance(v, dict):
            for k, x in v.items():
                assert isinstance(k, str), f"{p.name} contains non-string key"
                _walk(x)
            return
        raise AssertionError(f"{p.name} contains non-JSON value type: {type(v)}")
    _walk(data)
    return data


def test_pipeline_writes_required_artifacts_and_valid_json() -> None:
    _clean_outputs_dir()
    _run_pipeline()

    assert OUTPUTS.exists() and OUTPUTS.is_dir()
    paths = {name: OUTPUTS / name for name in REQUIRED}
    for name, p in paths.items():
        assert p.exists() and p.is_file(), f"Missing required artifact: outputs/{name}"
        assert p.stat().st_size > 0, f"Artifact is empty: outputs/{name}"

    _load_json(paths["run_stamp.json"])
    _load_json(paths["results.json"])

    log_text = paths["run.log"].read_text(encoding="utf-8", errors="replace")
    assert log_text.strip(), "run.log must contain at least one non-whitespace character"
    assert "TODO" not in log_text, "run.log must not contain TODO markers"


def test_pipeline_is_deterministic_and_overwrites_outputs() -> None:
    _clean_outputs_dir()
    _run_pipeline()
    first = {name: _sha256(OUTPUTS / name) for name in REQUIRED}
    first_json = {j: _load_json(OUTPUTS / j) for j in ("run_stamp.json", "results.json")}

    _run_pipeline()
    second = {name: _sha256(OUTPUTS / name) for name in REQUIRED}
    second_json = {j: _load_json(OUTPUTS / j) for j in ("run_stamp.json", "results.json")}

    assert first == second, "Artifacts must be byte-for-byte deterministic across runs"
    assert first_json["run_stamp.json"].keys() == second_json["run_stamp.json"].keys()
    assert first_json["results.json"].keys() == second_json["results.json"].keys()


from pathlib import Path
import json

target_path = Path('/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution').joinpath('tests/test_pipeline_outputs.py')
target_path.parent.mkdir(parents=True, exist_ok=True)
chunks = [Path(__file__).read_text(encoding="utf-8")]
final_text = '\n'.join(block.strip('\n') for block in chunks).strip() + '\n'
target_path.write_text(final_text, encoding='utf-8')
print('FILE_WRITTEN:tests/test_pipeline_outputs.py')
print('DIR_STATE:' + json.dumps(sorted(str(p.relative_to(Path("/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution"))) for p in target_path.parent.glob('*') if p.is_file())))
print("Summary: Added pytest coverage to run the pipeline and verify required outputs exist, validate JSON structure, and enforce deterministic overwriting across consecutive runs.")
