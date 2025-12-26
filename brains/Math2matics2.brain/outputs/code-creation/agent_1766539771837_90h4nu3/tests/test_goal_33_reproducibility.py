import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def _stable_json_payload(d: dict) -> dict:
    """Return a subset of fields expected to be reproducible across runs."""
    # Keep summary/stat fields + config-like metadata; drop timestamps / host info if present.
    drop = {
        "timestamp",
        "created_at",
        "datetime",
        "run_id",
        "hostname",
        "platform",
        "python",
        "argv",
    }
    out = {}
    for k, v in d.items():
        if k in drop:
            continue
        out[k] = v
    return out


def _stable_json_digest(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    payload = _stable_json_payload(data)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return _sha256_bytes(canonical.encode("utf-8"))


def _run_toy_experiment(outdir: Path, seed: int = 123) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "src" / "goal_33_toy_experiment.py"
    assert script.is_file(), f"Missing toy experiment script at {script}"
    outdir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.setdefault("PYTHONHASHSEED", "0")
    env.setdefault("MPLBACKEND", "Agg")

    cmd = [
        sys.executable,
        str(script),
        "--outdir",
        str(outdir),
        "--seed",
        str(seed),
    ]
    subprocess.run(cmd, cwd=str(repo_root), env=env, check=True)
def test_goal_33_reproducibility(tmp_path: Path) -> None:
    run1 = tmp_path / "run1"
    run2 = tmp_path / "run2"

    _run_toy_experiment(run1, seed=123)
    _run_toy_experiment(run2, seed=123)

    r1 = run1 / "results.json"
    r2 = run2 / "results.json"
    f1 = run1 / "figure.png"
    f2 = run2 / "figure.png"

    assert r1.is_file() and r2.is_file()
    assert f1.is_file() and f2.is_file()

    # Compare deterministic summary fields via a canonical digest.
    assert _stable_json_digest(r1) == _stable_json_digest(r2)

    # Optional: if the PNG is produced deterministically, this will hold; it is a strong
    # regression signal in CI. If you later need to relax this, compare only existence/size.
    assert _sha256_bytes(f1.read_bytes()) == _sha256_bytes(f2.read_bytes())
