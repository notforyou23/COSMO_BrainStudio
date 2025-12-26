import hashlib
import os
import runpy
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


def _find_entry_script(project_root: Path) -> Path:
    candidates = [
        project_root / "src" / "run_experiment.py",
        project_root / "run_experiment.py",
        project_root / "src" / "main.py",
        project_root / "main.py",
        project_root / "src" / "run.py",
        project_root / "run.py",
    ]
    for p in candidates:
        if p.is_file():
            return p
    raise FileNotFoundError(f"Could not find entry script. Tried: {[str(p) for p in candidates]}")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _artifact_manifest(root: Path):
    ignore_dirs = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache"}
    ignore_suffixes = {".pyc"}
    items = []
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if any(part in ignore_dirs for part in rel.parts):
            continue
        if p.is_dir():
            continue
        if p.suffix in ignore_suffixes:
            continue
        # Exclude any local python source copied into run directory (shouldn't happen; keep focused on produced artifacts)
        if rel.parts and rel.parts[0] in {"src", "tests"} and p.suffix in {".py", ".md", ".toml", ".lock", ".json", ".yaml", ".yml"}:
            continue
        st = p.stat()
        items.append((str(rel).replace(os.sep, "/"), st.st_size, _sha256_file(p)))
    return items


def _manifest_digest(manifest) -> str:
    h = hashlib.sha256()
    for rel, size, dig in manifest:
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(str(size).encode("utf-8"))
        h.update(b"\0")
        h.update(dig.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def _run_entry(entry_script: Path, project_root: Path, run_dir: Path):
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    wrapper = r'''
import os, random, runpy, sys
seed = int(os.environ.get("SEED", "0"))
os.environ.setdefault("PYTHONHASHSEED", str(seed))
random.seed(seed)
try:
    import numpy as np
    np.random.seed(seed)
except Exception:
    pass

# If project provides reproducibility helper, prefer it.
try:
    from src.utils.repro import set_seed as _set_seed
    try:
        _set_seed(seed=seed, deterministic=True)
    except TypeError:
        _set_seed(seed)
except Exception:
    # Best-effort torch determinism without project helper.
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        try:
            torch.use_deterministic_algorithms(True)
        except Exception:
            pass
        try:
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
        except Exception:
            pass
    except Exception:
        pass

script = os.environ["ENTRY_SCRIPT"]
runpy.run_path(script, run_name="__main__")
'''
    env = os.environ.copy()
    env.update(
        {
            "SEED": "0",
            "PYTHONHASHSEED": "0",
            "ENTRY_SCRIPT": str(entry_script),
            "PYTHONPATH": str(project_root),
            # common determinism knobs (harmless if unused)
            "CUBLAS_WORKSPACE_CONFIG": ":4096:8",
            "CUDA_LAUNCH_BLOCKING": "1",
            "TF_DETERMINISTIC_OPS": "1",
        }
    )
    subprocess.run([sys.executable, "-c", wrapper], cwd=str(run_dir), env=env, check=True)


@pytest.mark.timeout(300)
def test_end_to_end_determinism():
    project_root = Path(__file__).resolve().parents[1]
    entry_script = _find_entry_script(project_root)

    base = project_root / ".determinism_runs"
    run1 = base / "run1"
    run2 = base / "run2"

    _run_entry(entry_script, project_root, run1)
    _run_entry(entry_script, project_root, run2)

    m1 = _artifact_manifest(run1)
    m2 = _artifact_manifest(run2)

    d1 = _manifest_digest(m1)
    d2 = _manifest_digest(m2)

    if d1 != d2:
        s1, s2 = set(m1), set(m2)
        only1 = sorted(s1 - s2)[:20]
        only2 = sorted(s2 - s1)[:20]
        msg = [
            f"Artifact digests differ: run1={d1} run2={d2}",
            f"run1 files={len(m1)} run2 files={len(m2)}",
        ]
        if only1:
            msg.append("Only in run1 (first 20): " + ", ".join(x[0] for x in only1))
        if only2:
            msg.append("Only in run2 (first 20): " + ", ".join(x[0] for x in only2))
        pytest.fail("\n".join(msg))

    assert d1 == d2
