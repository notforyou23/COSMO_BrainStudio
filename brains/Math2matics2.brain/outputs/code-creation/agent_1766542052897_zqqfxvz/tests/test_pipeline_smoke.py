import json
import os
import subprocess
import sys
from pathlib import Path
import inspect


REQUIRED_FILES = [
    "results.json",
    "figure.png",
    "run.log",
    "test.log",
    "STATUS.md",
]


def _try_call_module(output_dir: Path) -> bool:
    try:
        import scripts.run_evidence_pack as m  # type: ignore
    except Exception:
        return False
    main = getattr(m, "main", None)
    if not callable(main):
        return False

    try:
        sig = inspect.signature(main)
    except Exception:
        sig = None

    try:
        if sig and len(sig.parameters) == 0:
            main()
        elif sig and list(sig.parameters)[0] in {"argv", "args"}:
            main(["--output-dir", str(output_dir)])
        elif sig and "output_dir" in sig.parameters:
            main(output_dir=str(output_dir))
        else:
            main(["--output-dir", str(output_dir)])
        return True
    except Exception:
        return False


def _run_subprocess(output_dir: Path) -> bool:
    cmds = [
        [sys.executable, "-m", "scripts.run_evidence_pack", "--output-dir", str(output_dir)],
        [sys.executable, "scripts/run_evidence_pack.py", "--output-dir", str(output_dir)],
        [sys.executable, "-m", "scripts.run_evidence_pack"],
        [sys.executable, "scripts/run_evidence_pack.py"],
    ]
    for cmd in cmds:
        p = subprocess.run(cmd, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        if p.returncode == 0:
            return True
    return False


def _pick_outputs_dir(preferred: Path) -> Path:
    if all((preferred / f).exists() for f in REQUIRED_FILES):
        return preferred
    repo_outputs = Path(__file__).resolve().parents[1] / "outputs"
    if all((repo_outputs / f).exists() for f in REQUIRED_FILES):
        return repo_outputs
    return preferred


def test_pipeline_smoke_creates_evidence_pack(tmp_path):
    outdir = tmp_path / "outputs"
    outdir.mkdir(parents=True, exist_ok=True)

    ran = _try_call_module(outdir) or _run_subprocess(outdir)
    assert ran, "Could not run pipeline via module import or subprocess invocation."

    outputs = _pick_outputs_dir(outdir)
    missing = [f for f in REQUIRED_FILES if not (outputs / f).is_file()]
    assert not missing, f"Missing required artifacts in {outputs}: {missing}"

    results_path = outputs / "results.json"
    data = json.loads(results_path.read_text(encoding="utf-8"))
    assert isinstance(data, dict) and data, "results.json must be a non-empty JSON object"

    fig = outputs / "figure.png"
    assert fig.stat().st_size > 100, "figure.png looks too small to be a real image"

    for log_name in ["run.log", "test.log"]:
        lp = outputs / log_name
        txt = lp.read_text(encoding="utf-8", errors="ignore")
        assert len(txt.strip()) > 0, f"{log_name} must be non-empty"

    status = (outputs / "STATUS.md").read_text(encoding="utf-8", errors="ignore")
    assert "outputs" in status.lower() or "results.json" in status.lower(), "STATUS.md should describe outputs"
