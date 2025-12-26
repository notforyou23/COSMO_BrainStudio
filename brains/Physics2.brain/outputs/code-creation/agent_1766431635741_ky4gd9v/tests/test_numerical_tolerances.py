"""Numerical tolerance tests for recomputed benchmark outputs.

These tests compare recomputed JSON outputs to the committed expected outputs,
allowing small floating-point drift via explicit acceptance criteria.
"""

from __future__ import annotations

from pathlib import Path
import math
import numbers
import subprocess
import sys
from typing import Any

import pytest

from .conftest import expected_outputs_dir, iter_json_files, read_json
REL_TOL = 1e-7
ABS_TOL = 1e-9


def _find_recompute_script(project_root: Path) -> Path | None:
    for p in (project_root / "scripts" / "recompute_outputs.py", project_root / "recompute_outputs.py"):
        if p.is_file():
            return p
    return None


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


def _iter_output_json_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return [p for p in iter_json_files(root) if "schemas" not in p.parts]
def _is_number(x: Any) -> bool:
    return isinstance(x, numbers.Real) and not isinstance(x, bool)


def _compare(a: Any, b: Any, *, path: str, diffs: list[str], rel_tol: float, abs_tol: float) -> None:
    if _is_number(a) and _is_number(b):
        # Treat ints exactly; floats (or mixed) with tolerance.
        if isinstance(a, int) and isinstance(b, int):
            if a != b:
                diffs.append(f"{path}: {a} != {b}")
            return
        af, bf = float(a), float(b)
        if math.isnan(af) or math.isnan(bf):
            if not (math.isnan(af) and math.isnan(bf)):
                diffs.append(f"{path}: NaN mismatch ({af} vs {bf})")
            return
        if not math.isclose(af, bf, rel_tol=rel_tol, abs_tol=abs_tol):
            diffs.append(f"{path}: {af} != {bf} (rel_tol={rel_tol}, abs_tol={abs_tol})")
        return

    if type(a) != type(b):
        diffs.append(f"{path}: type mismatch ({type(a).__name__} vs {type(b).__name__})")
        return

    if isinstance(a, dict):
        ka, kb = set(a.keys()), set(b.keys())
        if ka != kb:
            diffs.append(f"{path}: key set mismatch (missing={sorted(kb-ka)}, extra={sorted(ka-kb)})")
        for k in sorted(ka & kb):
            _compare(a[k], b[k], path=f"{path}/{k}", diffs=diffs, rel_tol=rel_tol, abs_tol=abs_tol)
        return

    if isinstance(a, list):
        if len(a) != len(b):
            diffs.append(f"{path}: list length {len(a)} != {len(b)}")
        for i, (ai, bi) in enumerate(zip(a, b)):
            _compare(ai, bi, path=f"{path}[{i}]", diffs=diffs, rel_tol=rel_tol, abs_tol=abs_tol)
        return

    if a != b:
        diffs.append(f"{path}: {a!r} != {b!r}")
def test_recomputed_outputs_within_numerical_tolerances(project_root: Path, outputs_dir: Path, tmp_path: Path) -> None:
    script_path = _find_recompute_script(project_root)
    if script_path is None:
        pytest.skip("Recompute script not found; skipping numerical tolerance comparisons.")

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

    failures: list[str] = []
    for rel in sorted(exp_rel):
        expected = read_json(exp_rel[rel])
        generated = read_json(gen_rel[rel])
        diffs: list[str] = []
        _compare(generated, expected, path="<root>", diffs=diffs, rel_tol=REL_TOL, abs_tol=ABS_TOL)
        if diffs:
            snippet = "\n".join("  - " + d for d in diffs[:50])
            more = "" if len(diffs) <= 50 else f"\n  ... {len(diffs)-50} more"
            failures.append(f"{rel} failed numerical tolerance comparison:\n{snippet}{more}")

    assert not failures, "\n\n".join(failures)
