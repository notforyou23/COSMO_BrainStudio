"""Deterministic recomputation tests for committed benchmark outputs.

This suite runs the project's recomputation script into a temporary directory and
asserts that the generated JSON outputs are byte-identical to the committed
expected outputs (when present).
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

from .conftest import expected_outputs_dir, iter_json_files


def _find_recompute_script(project_root: Path) -> Path | None:
    """Locate the standalone recomputation script, if available."""
    candidates = [
        project_root / "scripts" / "recompute_outputs.py",
        project_root / "recompute_outputs.py",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def _iter_output_json_files(root: Path) -> list[Path]:
    """Return candidate output JSON files, excluding schemas."""
    if not root.exists():
        return []
    files = [p for p in iter_json_files(root) if "schemas" not in p.parts]
    return files


def _run_recompute(script_path: Path, *, out_dir: Path, project_root: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(script_path), "--output-dir", str(out_dir)]
    proc = subprocess.run(
        cmd,
        cwd=str(project_root),
        check=False,
        capture_output=True,
        text=True,
        env={**dict(**__import__("os").environ), "PYTHONHASHSEED": "0"},
    )
    if proc.returncode != 0:
        raise AssertionError(
            "Recompute script failed.\n"
            f"cmd: {cmd}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )


def _read_bytes(p: Path) -> bytes:
    return p.read_bytes().replace(b"\r\n", b"\n")
def test_recompute_outputs_match_expected(project_root: Path, outputs_dir: Path, tmp_path: Path) -> None:
    script_path = _find_recompute_script(project_root)
    if script_path is None:
        pytest.skip("Recompute script not found (scripts/recompute_outputs.py); skipping determinism test.")

    expected_dir = expected_outputs_dir(outputs_dir)
    expected_files = _iter_output_json_files(expected_dir)
    if not expected_files:
        pytest.skip("No committed expected benchmark JSON outputs found under outputs/ (or outputs/expected).")

    gen_dir = tmp_path / "outputs_gen"
    _run_recompute(script_path, out_dir=gen_dir, project_root=project_root)

    gen_files = _iter_output_json_files(gen_dir)
    exp_rel = {p.relative_to(expected_dir).as_posix(): p for p in expected_files}
    gen_rel = {p.relative_to(gen_dir).as_posix(): p for p in gen_files}

    assert set(gen_rel) == set(exp_rel), (
        "Generated outputs file set differs from expected outputs.\n"
        f"Missing: {sorted(set(exp_rel) - set(gen_rel))}\n"
        f"Extra:   {sorted(set(gen_rel) - set(exp_rel))}"
    )

    diffs: list[str] = []
    for rel in sorted(exp_rel):
        exp_p, gen_p = exp_rel[rel], gen_rel[rel]
        if _read_bytes(exp_p) != _read_bytes(gen_p):
            diffs.append(rel)

    assert not diffs, "Byte-stable mismatch for:\n" + "\n".join(f"  - {d}" for d in diffs)
def test_recompute_is_deterministic_across_two_runs(project_root: Path, outputs_dir: Path, tmp_path: Path) -> None:
    script_path = _find_recompute_script(project_root)
    if script_path is None:
        pytest.skip("Recompute script not found (scripts/recompute_outputs.py); skipping determinism test.")

    expected_dir = expected_outputs_dir(outputs_dir)
    if not _iter_output_json_files(expected_dir):
        pytest.skip("No committed expected outputs found; skipping determinism check.")

    gen_a = tmp_path / "outputs_run_a"
    gen_b = tmp_path / "outputs_run_b"
    _run_recompute(script_path, out_dir=gen_a, project_root=project_root)
    _run_recompute(script_path, out_dir=gen_b, project_root=project_root)

    files_a = {p.relative_to(gen_a).as_posix(): p for p in _iter_output_json_files(gen_a)}
    files_b = {p.relative_to(gen_b).as_posix(): p for p in _iter_output_json_files(gen_b)}

    assert set(files_a) == set(files_b), "Recompute produced different file sets across runs."
    diffs = [rel for rel in sorted(files_a) if _read_bytes(files_a[rel]) != _read_bytes(files_b[rel])]
    assert not diffs, "Recompute is not deterministic across runs for:\n" + "\n".join(f"  - {d}" for d in diffs)
