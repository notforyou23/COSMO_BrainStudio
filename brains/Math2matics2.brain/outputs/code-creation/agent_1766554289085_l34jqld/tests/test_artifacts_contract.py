from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTDIR = REPO_ROOT / "outputs"


def _run_pipeline(outdir: Path) -> None:
    outdir = Path(outdir)
    outdir.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.setdefault("PYTHONHASHSEED", "0")
    env.setdefault("MPLBACKEND", "Agg")

    cmd = [sys.executable, "-m", "src.run_pipeline", "--outdir", str(outdir)]
    try:
        subprocess.run(cmd, cwd=str(REPO_ROOT), env=env, check=True, capture_output=True, text=True)
        return
    except subprocess.CalledProcessError:
        # Fallback to default CLI behavior (no --outdir)
        cmd2 = [sys.executable, "-m", "src.run_pipeline"]
        subprocess.run(cmd2, cwd=str(REPO_ROOT), env=env, check=True, capture_output=True, text=True)


def _load_json(p: Path) -> dict:
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def _schema_dict():
    import src.schema as schema  # type: ignore

    for name in ("ARTIFACT_SCHEMA", "RESULTS_SCHEMA", "SCHEMA"):
        if hasattr(schema, name):
            d = getattr(schema, name)
            if isinstance(d, dict):
                return d
    raise AssertionError("src.schema must expose ARTIFACT_SCHEMA or RESULTS_SCHEMA as a dict")


def _assert_exact_keys(obj: dict, schema: dict, *, where: str) -> None:
    props = schema.get("properties")
    if not isinstance(props, dict) or not props:
        req = schema.get("required")
        if isinstance(req, list) and req:
            expected = set(req)
            assert set(obj.keys()) >= expected, f"{where}: missing required keys {sorted(expected - set(obj.keys()))}"
            return
        raise AssertionError(f"{where}: schema missing 'properties' (preferred) and 'required'")

    expected = set(props.keys())
    got = set(obj.keys())
    assert got == expected, f"{where}: keys mismatch. expected={sorted(expected)} got={sorted(got)}"


def _iter_numeric_paths(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            yield from _iter_numeric_paths(v, p)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            p = f"{prefix}[{i}]"
            yield from _iter_numeric_paths(v, p)
    else:
        if isinstance(obj, (int, float)) and not isinstance(obj, bool):
            yield prefix, float(obj)


def _assert_numeric_tolerances(results: dict) -> None:
    # Prefer schema-provided numeric expectations if present
    import src.schema as schema  # type: ignore

    if hasattr(schema, "TOLERANCES") and isinstance(schema.TOLERANCES, dict):
        for path, spec in schema.TOLERANCES.items():
            cur = results
            for part in str(path).split("."):
                if not part:
                    continue
                if not isinstance(cur, dict) or part not in cur:
                    raise AssertionError(f"Missing numeric field for tolerance check: {path}")
                cur = cur[part]
            if not isinstance(cur, (int, float)) or isinstance(cur, bool):
                raise AssertionError(f"Field not numeric for tolerance check: {path}")
            if isinstance(spec, (list, tuple)) and len(spec) == 3:
                exp, atol, rtol = spec
                assert math.isfinite(cur)
                assert math.isclose(float(cur), float(exp), rel_tol=float(rtol), abs_tol=float(atol)), (
                    f"{path}: expected {exp} (atol={atol}, rtol={rtol}) got {cur}"
                )
            elif isinstance(spec, (list, tuple)) and len(spec) == 2:
                exp, atol = spec
                assert math.isfinite(cur)
                assert abs(float(cur) - float(exp)) <= float(atol), f"{path}: expected {exp}±{atol}, got {cur}"
            else:
                raise AssertionError(f"Invalid TOLERANCES spec for {path}: {spec}")
        return

    # Generic sanity checks if no explicit tolerances are provided.
    for path, val in _iter_numeric_paths(results):
        assert math.isfinite(val), f"{path}: non-finite numeric value"
    metrics = results.get("metrics")
    if isinstance(metrics, dict):
        for k in ("mean", "std"):
            if k in metrics and isinstance(metrics[k], (int, float)) and not isinstance(metrics[k], bool):
                v = float(metrics[k])
                if k == "mean":
                    assert 0.45 <= v <= 0.55, f"metrics.mean out of expected tolerance band: {v}"
                if k == "std":
                    assert 0.25 <= v <= 0.35, f"metrics.std out of expected tolerance band: {v}"


@pytest.mark.integration
def test_artifacts_contract(tmp_path: Path) -> None:
    outdir1 = tmp_path / "run1_outputs"
    outdir2 = tmp_path / "run2_outputs"

    # Ensure we start clean for default outputs if pipeline ignores --outdir
    if DEFAULT_OUTDIR.exists():
        shutil.rmtree(DEFAULT_OUTDIR)

    _run_pipeline(outdir1)
    outdir_effective = outdir1 if (outdir1 / "results.json").exists() else DEFAULT_OUTDIR

    results_path = outdir_effective / "results.json"
    fig_path = outdir_effective / "figure.png"
    assert results_path.is_file(), f"Missing results.json at {results_path}"
    assert fig_path.is_file(), f"Missing figure.png at {fig_path}"
    assert fig_path.stat().st_size > 0, "figure.png exists but is empty"

    results1 = _load_json(results_path)
    schema = _schema_dict()
    _assert_exact_keys(results1, schema, where="results.json (top-level)")

    # Re-run and assert determinism (exact JSON + non-empty figure)
    if DEFAULT_OUTDIR.exists() and outdir_effective == DEFAULT_OUTDIR:
        shutil.rmtree(DEFAULT_OUTDIR)
    _run_pipeline(outdir2)
    outdir_effective_2 = outdir2 if (outdir2 / "results.json").exists() else DEFAULT_OUTDIR

    results2 = _load_json(outdir_effective_2 / "results.json")
    assert results2 == results1, "results.json must be exactly identical across runs"
    fig2 = outdir_effective_2 / "figure.png"
    assert fig2.is_file() and fig2.stat().st_size > 0
    assert fig2.read_bytes() == fig_path.read_bytes(), "figure.png must be exactly identical across runs"

    _assert_numeric_tolerances(results1)
