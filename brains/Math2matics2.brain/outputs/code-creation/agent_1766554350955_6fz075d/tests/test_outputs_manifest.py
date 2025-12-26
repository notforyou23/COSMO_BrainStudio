from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PIPELINE = REPO_ROOT / "scripts" / "run_pipeline.py"
OUTPUTS_DIR = REPO_ROOT / "outputs"
MANIFEST_MD = OUTPUTS_DIR / "index.md"


def _run_pipeline() -> None:
    if not PIPELINE.is_file():
        raise AssertionError(f"Pipeline entrypoint not found: {PIPELINE}")
    env = os.environ.copy()
    env.setdefault("PYTHONHASHSEED", "0")
    base_cmd = [sys.executable, str(PIPELINE), "--output-dir", str(OUTPUTS_DIR)]
    candidates = [
        base_cmd + ["--ci"],
        base_cmd + ["--deterministic"],
        base_cmd,
    ]
    last_err = None
    for cmd in candidates:
        try:
            subprocess.run(cmd, cwd=str(REPO_ROOT), env=env, check=True, capture_output=True, text=True)
            return
        except subprocess.CalledProcessError as e:
            last_err = e
    assert last_err is not None
    raise AssertionError(
        "Pipeline failed to run.\n"
        f"cmd={last_err.cmd}\n"
        f"returncode={last_err.returncode}\n"
        f"stdout={last_err.stdout[-2000:]}\n"
        f"stderr={last_err.stderr[-2000:]}"
    )


def _parse_manifest_paths(manifest_text: str) -> list[Path]:
    # Prefer backticked relative paths; tolerate plain "outputs/..." paths.
    paths: list[str] = []
    paths += re.findall(r"`([^`]+)`", manifest_text)
    paths += re.findall(r"(?m)^(?:-|\*|\d+\.)\s+(outputs/[^\s\)]+)", manifest_text)
    cleaned: list[Path] = []
    for p in paths:
        p = p.strip()
        if not p or "://" in p:
            continue
        p = p.lstrip("./")
        if p.startswith("outputs/"):
            rel = Path(p)
        else:
            rel = Path("outputs") / p
        # Only keep plausible file paths (not directories/anchors)
        if rel.suffix and not any(part.startswith("#") for part in rel.parts):
            cleaned.append(rel)

    # De-duplicate preserving order
    seen: set[str] = set()
    out: list[Path] = []
    for rel in cleaned:
        key = rel.as_posix()
        if key not in seen:
            seen.add(key)
            out.append(rel)
    return out


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _hash_manifest_files(files: list[Path]) -> dict[str, str]:
    out: dict[str, str] = {}
    for rel in files:
        p = REPO_ROOT / rel
        if not p.is_file():
            raise AssertionError(f"Expected artifact missing: {rel}")
        out[rel.as_posix()] = _sha256(p)
    return out


def test_outputs_manifest_end_to_end_and_reproducible() -> None:
    _run_pipeline()
    assert MANIFEST_MD.is_file(), f"Missing manifest: {MANIFEST_MD}"

    text = MANIFEST_MD.read_text(encoding="utf-8")
    manifest_files = _parse_manifest_paths(text)
    assert manifest_files, "No artifact file paths could be parsed from outputs/index.md"

    first = _hash_manifest_files(manifest_files)

    _run_pipeline()
    second = _hash_manifest_files(manifest_files)

    assert first == second, "Artifacts are not reproducibly generated (content hashes changed between runs)
