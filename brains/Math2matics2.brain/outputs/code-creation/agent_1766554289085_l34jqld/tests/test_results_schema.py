from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_json_text(path: Path) -> str:
    assert path.exists(), f"Missing artifact: {path}"
    return path.read_text(encoding="utf-8")


def _load_ordered(json_text: str):
    return json.loads(json_text, object_pairs_hook=list)


def _pairs_to_dict(pairs):
    return {k: v for k, v in pairs}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_sha256_hex(s: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{64}", s or ""))


def test_results_schema_and_hashes():
    root = _repo_root()
    outputs = root / "outputs"
    results_path = outputs / "results.json"
    fig_path = outputs / "figure.png"
    hashes_path = outputs / "hashes.json"

    results_text = _read_json_text(results_path)
    hashes_text = _read_json_text(hashes_path)

    results_pairs = _load_ordered(results_text)
    assert isinstance(results_pairs, list), "results.json must be a JSON object"
    results = _pairs_to_dict(results_pairs)

    expected_top_keys = ["schema_version", "seed", "metrics", "artifacts"]
    assert [k for k, _ in results_pairs] == expected_top_keys, "Top-level key order must be stable"
    assert set(results.keys()) == set(expected_top_keys), "Unexpected/missing keys in results.json"

    assert isinstance(results["schema_version"], int)
    assert isinstance(results["seed"], int)

    metrics = results["metrics"]
    assert isinstance(metrics, dict)
    for k in ["n", "mean", "std"]:
        assert k in metrics
    assert isinstance(metrics["n"], int) and metrics["n"] >= 1
    assert isinstance(metrics["mean"], (int, float))
    assert isinstance(metrics["std"], (int, float))

    artifacts = results["artifacts"]
    assert isinstance(artifacts, dict)
    for k in ["results_json", "figure_png"]:
        assert k in artifacts and isinstance(artifacts[k], str)
    assert artifacts["results_json"].endswith("outputs/results.json")
    assert artifacts["figure_png"].endswith("outputs/figure.png")

    # Stable serialization check: indent=2, no key sorting, newline at end.
    canonical = json.dumps(results, indent=2, sort_keys=False, ensure_ascii=False) + "\n"
    assert results_text == canonical, "results.json must be written with stable formatting"

    hashes = json.loads(hashes_text)
    assert isinstance(hashes, dict), "hashes.json must be a JSON object"
    for key in ["outputs/results.json", "outputs/figure.png"]:
        assert key in hashes, f"hashes.json missing entry for {key}"
        assert isinstance(hashes[key], str) and _is_sha256_hex(hashes[key])

    assert fig_path.exists(), f"Missing artifact: {fig_path}"
    assert hashes["outputs/results.json"] == _sha256_file(results_path)
    assert hashes["outputs/figure.png"] == _sha256_file(fig_path)
