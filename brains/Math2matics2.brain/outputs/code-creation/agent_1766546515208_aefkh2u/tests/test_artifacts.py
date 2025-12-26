import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _find_entrypoint(repo: Path) -> Path:
    # Prefer likely entrypoints, else fall back to any top-level *.py with __main__ guard.
    preferred = [
        repo / "main.py",
        repo / "run.py",
        repo / "app.py",
        repo / "run_pipeline.py",
        repo / "pipeline.py",
        repo / "generated_script_1766546521995.py",
        repo / "script.py",
    ]
    for p in preferred:
        if p.is_file():
            return p

    candidates = [p for p in repo.glob("*.py") if p.name != "conftest.py"]
    for p in candidates:
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if re.search(r"if\s+__name__\s*==\s*['\"]__main__['\"]\s*:", txt):
            return p
    if candidates:
        return sorted(candidates)[0]
    raise FileNotFoundError("Could not locate a runnable entrypoint script in repo root")


def _run_entrypoint(entrypoint: Path, outdir: Path, seed: int = 123) -> None:
    # Try a small set of common CLI conventions (seed + output dir).
    attempts = [
        [sys.executable, str(entrypoint), "--seed", str(seed), "--output-dir", str(outdir)],
        [sys.executable, str(entrypoint), "--seed", str(seed), "--outdir", str(outdir)],
        [sys.executable, str(entrypoint), "--seed", str(seed), "--output", str(outdir)],
        [sys.executable, str(entrypoint), "--seed", str(seed), str(outdir)],
        [sys.executable, str(entrypoint), str(outdir), "--seed", str(seed)],
        [sys.executable, str(entrypoint)],
    ]
    env = os.environ.copy()
    env.setdefault("PYTHONHASHSEED", "0")
    env.setdefault("SEED", str(seed))
    env.setdefault("OUTPUT_DIR", str(outdir))

    last = None
    for cmd in attempts:
        last = subprocess.run(cmd, cwd=str(_repo_root()), env=env, capture_output=True, text=True, timeout=180)
        if last.returncode == 0:
            return
    msg = (last.stdout[-2000:] if last else "") + "\n" + (last.stderr[-2000:] if last else "")
    raise AssertionError(f"Entrypoint failed for all CLI patterns. Last output:\n{msg}")


def _pick_manifest_json(outdir: Path) -> Path:
    preferred = ["artifacts.json", "manifest.json", "output.json", "outputs.json", "results.json", "report.json"]
    for name in preferred:
        p = outdir / name
        if p.is_file():
            return p
    js = sorted(outdir.glob("*.json"))
    if not js:
        raise AssertionError(f"No JSON artifacts found in {outdir}")
    return js[0]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def _validate_json_schema(data: dict) -> None:
    assert isinstance(data, dict) and data, "Top-level JSON must be a non-empty object"
    seed_keys = {"seed", "random_seed", "rng_seed"}
    assert (seed_keys & set(data.keys())) or (str(data.get("metadata", {}).get("seed", "")) != ""), (
        "JSON must include a seed (seed/random_seed/rng_seed) or metadata.seed"
    )
    # Require at least one of these keys to ensure a stable-ish contract across runs.
    contract_keys = {"artifacts", "outputs", "files", "results", "images"}
    assert contract_keys & set(data.keys()), f"JSON missing expected contract keys; got: {sorted(data.keys())}"


def _validate_output_files(outdir: Path, manifest: dict) -> None:
    # If manifest lists artifacts with paths, ensure they exist.
    def iter_paths(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in {"path", "filepath", "file", "filename"} and isinstance(v, str):
                    yield v
                yield from iter_paths(v)
        elif isinstance(obj, list):
            for it in obj:
                yield from iter_paths(it)

    for rel in set(iter_paths(manifest)):
        p = (outdir / rel).resolve() if not Path(rel).is_absolute() else Path(rel)
        # Only enforce paths under outdir to avoid accidental absolute references.
        if outdir.resolve() in p.parents or p == outdir.resolve():
            assert p.exists(), f"Manifest references missing file: {rel}"


def _validate_images(outdir: Path) -> None:
    imgs = list(outdir.rglob("*.png")) + list(outdir.rglob("*.jpg")) + list(outdir.rglob("*.jpeg"))
    for p in imgs:
        size = p.stat().st_size
        assert 1_000 <= size <= 10_000_000, f"Unexpected image size for {p.name}: {size} bytes"
        # Hash is useful for debugging; we don't pin it to avoid brittleness across platforms.
        _ = _sha256(p)


@pytest.mark.smoke
def test_artifacts_end_to_end(tmp_path: Path):
    repo = _repo_root()
    entrypoint = _find_entrypoint(repo)

    outdir = tmp_path / "out"
    outdir.mkdir(parents=True, exist_ok=True)

    _run_entrypoint(entrypoint, outdir, seed=123)

    # Existence checks
    json_path = _pick_manifest_json(outdir)
    assert json_path.exists(), "Expected a JSON artifact to be created"
    assert any(outdir.iterdir()), "Output directory is empty after successful run"

    manifest = json.loads(json_path.read_text(encoding="utf-8"))
    _validate_json_schema(manifest)
    _validate_output_files(outdir, manifest)
    _validate_images(outdir)
