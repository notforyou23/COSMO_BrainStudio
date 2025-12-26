from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path

import pytest
def _project_root() -> Path:
    # tests/ -> project root
    return Path(__file__).resolve().parents[1]


def _import_pipeline_module():
    root = _project_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    # Primary expected location
    try:
        return importlib.import_module("src.repro_json_pipeline")
    except ModuleNotFoundError:
        # Fallback if module is at top-level
        return importlib.import_module("repro_json_pipeline")
def _run_pipeline(mod, seed: int, output_path: Path):
    # Try a small set of common entrypoints/signatures.
    # Must accept seed deterministically and write results.json.
    candidates = [
        ("run_pipeline", {"seed": seed, "output_path": str(output_path)}),
        ("run_pipeline", {"seed": seed, "output_path": output_path}),
        ("run_pipeline", {"seed": seed, "output_dir": str(output_path.parent)}),
        ("run_pipeline", {"seed": seed}),
        ("run", {"seed": seed, "output_path": str(output_path)}),
        ("run", {"seed": seed, "output_path": output_path}),
        ("run", {"seed": seed, "output_dir": str(output_path.parent)}),
        ("run", {"seed": seed}),
        ("main", {"seed": seed, "output_path": str(output_path)}),
        ("main", {"seed": seed}),
    ]

    last_err = None
    for fname, kwargs in candidates:
        fn = getattr(mod, fname, None)
        if fn is None:
            continue
        try:
            return fn(**kwargs)
        except TypeError as e:
            last_err = e
            continue

    raise AssertionError(
        "Could not execute pipeline; no compatible entrypoint found. "
        f"Tried {[c[0] for c in candidates]} with seed/output variants. "
        f"Last error: {last_err!r}"
    )
def test_import_and_run_creates_deterministic_results_json(tmp_path, monkeypatch):
    mod = _import_pipeline_module()

    root = _project_root()
    monkeypatch.chdir(root)

    outputs_dir = root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    results_path = outputs_dir / "results.json"
    if results_path.exists():
        results_path.unlink()

    seed = 12345
    _run_pipeline(mod, seed=seed, output_path=results_path)
    assert results_path.exists(), f"Expected results artifact at {results_path}"

    first_bytes = results_path.read_bytes()
    first_obj = json.loads(first_bytes.decode("utf-8"))
    assert isinstance(first_obj, dict), "results.json must contain a JSON object"

    # Re-run with same seed and ensure determinism (byte-identical output file).
    _run_pipeline(mod, seed=seed, output_path=results_path)
    second_bytes = results_path.read_bytes()
    assert second_bytes == first_bytes, "results.json must be deterministic for a fixed seed"

    # Basic minimal sanity fields (non-strict; allow future expansion)
    assert "seed" in first_obj, "results.json should include the seed used"
    assert int(first_obj["seed"]) == seed
