import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def _artifact_hashes(root: Path) -> dict:
    ignore_suffix = {".log", ".tmp", ".lock"}
    ignore_names = {"stdout.txt", "stderr.txt"}
    hashes = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if p.name in ignore_names:
            continue
        if p.suffix.lower() in ignore_suffix:
            continue
        rel = str(p.relative_to(root)).replace(os.sep, "/")
        hashes[rel] = _sha256_file(p)
    return hashes


def _find_entrypoint(repo_root: Path) -> Path | None:
    candidates = [
        repo_root / "src" / "run_experiment.py",
        repo_root / "run_experiment.py",
        repo_root / "src" / "main.py",
        repo_root / "main.py",
        repo_root / "src" / "__main__.py",
        repo_root / "__main__.py",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def _run_entrypoint(repo_root: Path, entrypoint: Path, out_dir: Path) -> None:
    env = os.environ.copy()
    env.update(
        {
            "PYTHONHASHSEED": "0",
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
            "CUBLAS_WORKSPACE_CONFIG": ":4096:8",
            "CUDA_LAUNCH_BLOCKING": "1",
            "SEED": "0",
            "OUTPUT_DIR": str(out_dir),
            "OUT_DIR": str(out_dir),
            "ARTIFACT_DIR": str(out_dir),
            "PYTHONPATH": str(repo_root) + (os.pathsep + env.get("PYTHONPATH", "") if env.get("PYTHONPATH") else ""),
        }
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(entrypoint)]
    subprocess.run(cmd, cwd=str(repo_root), env=env, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)


@pytest.mark.parametrize("seed", [0])
def test_end_to_end_determinism(seed: int) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    entrypoint = _find_entrypoint(repo_root)
    if entrypoint is None:
        pytest.skip("No known entrypoint found (expected src/run_experiment.py or similar).")

    with tempfile.TemporaryDirectory(prefix="det_run1_") as d1, tempfile.TemporaryDirectory(prefix="det_run2_") as d2:
        out1 = Path(d1) / "artifacts"
        out2 = Path(d2) / "artifacts"

        _run_entrypoint(repo_root, entrypoint, out1)
        _run_entrypoint(repo_root, entrypoint, out2)

        h1 = _artifact_hashes(out1)
        h2 = _artifact_hashes(out2)

        if not h1 and not h2:
            pytest.skip("Entrypoint produced no artifacts in OUTPUT_DIR/ARTIFACT_DIR; cannot assert determinism.")
        assert h1 == h2, f"Artifact hashes differ between runs.\nRun1 files: {sorted(h1)}\nRun2 files: {sorted(h2)}"
