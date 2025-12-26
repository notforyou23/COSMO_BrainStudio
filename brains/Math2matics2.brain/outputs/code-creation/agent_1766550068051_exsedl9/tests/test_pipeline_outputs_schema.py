import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_pipeline.py"


def _run_pipeline(workspace: Path, seed: int) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(REPO_ROOT), env.get("PYTHONPATH", "")]).strip(os.pathsep)
    cmd = [sys.executable, str(SCRIPT), "--seed", str(seed)]
    subprocess.run(cmd, cwd=str(workspace), env=env, check=True, capture_output=True, text=True)


def _png_signature_ok(p: Path) -> bool:
    sig = b"\x89PNG\r\n\x1a\n"
    return p.is_file() and p.read_bytes()[:8] == sig


def _load_results(workspace: Path) -> dict:
    results_path = workspace / "outputs" / "results.json"
    assert results_path.is_file(), f"Missing {results_path}"
    with results_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _validate_schema(results: dict, workspace: Path) -> None:
    assert isinstance(results, dict), "results.json must be an object"

    # Prefer validating against the canonical schema utilities if present.
    try:
        from src.pipeline import output_schema as oschema  # type: ignore
    except Exception:
        oschema = None

    if oschema is not None:
        for name in ("validate_results_dict", "validate_results", "validate_results_json", "validate_results_file"):
            fn = getattr(oschema, name, None)
            if callable(fn):
                try:
                    fn(results)  # dict validator
                    return
                except TypeError:
                    pass
                try:
                    fn(workspace / "outputs" / "results.json")  # path validator
                    return
                except TypeError:
                    pass

        keys = None
        for kname in ("CANONICAL_RESULTS_KEYS", "RESULTS_KEYS", "RESULTS_SCHEMA_KEYS"):
            keys = getattr(oschema, kname, None)
            if isinstance(keys, (list, tuple)) and all(isinstance(x, str) for x in keys):
                assert set(results.keys()) == set(keys)
                return

        schema = getattr(oschema, "RESULTS_SCHEMA", None)
        if isinstance(schema, dict):
            props = schema.get("properties")
            req = schema.get("required")
            if isinstance(req, list) and all(isinstance(x, str) for x in req):
                assert set(req).issubset(results.keys())
            if isinstance(props, dict):
                assert set(results.keys()).issubset(set(props.keys()))

    # Fallback minimal schema checks (kept strict but implementation-agnostic).
    required = {"schema_version", "seed", "metrics", "artifacts"}
    assert required.issubset(results.keys()), f"Missing required keys: {sorted(required - set(results.keys()))}"
    assert isinstance(results["seed"], int)
    assert isinstance(results["metrics"], dict)
    assert isinstance(results["artifacts"], dict)
    fig = results["artifacts"].get("figure_png") or results["artifacts"].get("figure") or results["artifacts"].get("figure_path")
    assert isinstance(fig, str)
    assert fig.replace("\\", "/").endswith("outputs/figure.png")


def test_pipeline_produces_canonical_outputs_and_schema(tmp_path: Path) -> None:
    _run_pipeline(tmp_path, seed=123)
    out_dir = tmp_path / "outputs"
    assert out_dir.is_dir(), "Missing outputs/ directory"
    assert (out_dir / "results.json").is_file()
    assert _png_signature_ok(out_dir / "figure.png"), "outputs/figure.png must be a valid PNG"
    results = _load_results(tmp_path)
    _validate_schema(results, tmp_path)


def test_pipeline_is_deterministic_under_fixed_seed(tmp_path: Path) -> None:
    ws1 = tmp_path / "run1"
    ws2 = tmp_path / "run2"
    ws1.mkdir()
    ws2.mkdir()

    _run_pipeline(ws1, seed=999)
    _run_pipeline(ws2, seed=999)

    r1 = (ws1 / "outputs" / "results.json").read_bytes()
    r2 = (ws2 / "outputs" / "results.json").read_bytes()
    assert r1 == r2, "results.json must be byte-for-byte identical under a fixed seed"

    f1 = (ws1 / "outputs" / "figure.png").read_bytes()
    f2 = (ws2 / "outputs" / "figure.png").read_bytes()
    assert f1 == f2, "figure.png must be byte-for-byte identical under a fixed seed"
