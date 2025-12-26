from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import hashlib
import json

import pytest


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs"
BASELINES = ROOT / "tests" / "baselines"
PIPELINE = ROOT / "scripts" / "run_pipeline.py"


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8").strip()


def _canonical_json_bytes(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hamming_hex(a_hex: str, b_hex: str) -> int:
    a = int(a_hex, 16)
    b = int(b_hex, 16)
    return (a ^ b).bit_count()


def _import_metrics():
    sys.path.insert(0, str(ROOT))
    try:
        from src.metrics import json_checksum, png_phash, hamming_distance  # type: ignore
        return json_checksum, png_phash, hamming_distance
    except Exception:
        try:
            from src.metrics import canonical_json_checksum as json_checksum  # type: ignore
        except Exception:
            json_checksum = None
        try:
            from src.metrics import image_phash as png_phash  # type: ignore
        except Exception:
            png_phash = None
        try:
            from src.metrics import hamming_distance  # type: ignore
        except Exception:
            hamming_distance = None
        return json_checksum, png_phash, hamming_distance


def _run_pipeline():
    assert PIPELINE.exists(), f"Missing pipeline script: {PIPELINE}"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(PIPELINE)], cwd=str(ROOT), check=True)


def _compute_json_checksum(path: Path) -> str:
    json_checksum, _, _ = _import_metrics()
    if callable(json_checksum):
        return str(json_checksum(path))
    obj = json.loads(path.read_text(encoding="utf-8"))
    return _sha256_hex(_canonical_json_bytes(obj))


def _compute_png_phash(path: Path) -> str:
    _, png_phash, _ = _import_metrics()
    if callable(png_phash):
        return str(png_phash(path))
    try:
        from PIL import Image  # type: ignore
    except Exception as e:
        raise RuntimeError("PIL/Pillow required for fallback PNG perceptual hash.") from e
    import numpy as np  # type: ignore

    img = Image.open(path).convert("L").resize((32, 32))
    arr = np.asarray(img, dtype=np.float32)
    dct = np.fft.fft2(arr)
    dct_low = np.abs(dct[:8, :8]).flatten()
    med = float(np.median(dct_low[1:]))
    bits = (dct_low > med).astype(int)
    v = 0
    for b in bits.tolist():
        v = (v << 1) | int(b)
    return f"{v:016x}"


def _hamming(a: str, b: str) -> int:
    _, _, hamming_distance = _import_metrics()
    if callable(hamming_distance):
        return int(hamming_distance(a, b))
    return _hamming_hex(a, b)


@pytest.mark.slow
def test_pipeline_outputs_stability():
    _run_pipeline()

    results_path = OUT_DIR / "results.json"
    fig_path = OUT_DIR / "figure.png"
    assert results_path.exists(), f"Missing output: {results_path}"
    assert fig_path.exists(), f"Missing output: {fig_path}"

    got_json = _compute_json_checksum(results_path)
    got_phash = _compute_png_phash(fig_path)

    baseline_json_path = BASELINES / "results_checksum.txt"
    baseline_phash_path = BASELINES / "figure_phash.txt"
    assert baseline_json_path.exists(), f"Missing baseline: {baseline_json_path}"
    assert baseline_phash_path.exists(), f"Missing baseline: {baseline_phash_path}"

    exp_json = _read_text(baseline_json_path)
    exp_phash = _read_text(baseline_phash_path)

    assert got_json == exp_json, (
        "Canonical JSON checksum drift detected.\n"
        f"expected={exp_json}\n"
        f"got={got_json}"
    )

    dist = _hamming(got_phash, exp_phash)
    max_dist = 6
    assert dist <= max_dist, (
        "Figure perceptual-hash drift detected.\n"
        f"expected={exp_phash}\n"
        f"got={got_phash}\n"
        f"hamming={dist} (max={max_dist})"
    )
