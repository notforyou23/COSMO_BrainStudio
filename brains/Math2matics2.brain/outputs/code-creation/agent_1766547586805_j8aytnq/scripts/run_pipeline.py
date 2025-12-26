from __future__ import annotations

from pathlib import Path
import json
import hashlib

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs"
RESULTS_PATH = OUT_DIR / "results.json"
FIG_PATH = OUT_DIR / "figure.png"
BASELINE_PATH = OUT_DIR / "baselines.json"

SEED = 1337
N = 120


def canonical_json_bytes(obj) -> bytes:
    s = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return s.encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dhash_hex_png(path: Path, hash_size: int = 8) -> str:
    img = Image.open(path).convert("L").resize((hash_size + 1, hash_size), Image.Resampling.BILINEAR)
    arr = np.asarray(img, dtype=np.uint8)
    diff = arr[:, 1:] > arr[:, :-1]
    bits = diff.flatten()
    val = 0
    for b in bits:
        val = (val << 1) | int(b)
    width = (hash_size * hash_size + 3) // 4
    return f"{val:0{width}x}"


def hamming_hex(a: str, b: str) -> int:
    ai, bi = int(a, 16), int(b, 16)
    return (ai ^ bi).bit_count()


def run() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rng = np.random.RandomState(SEED)
    x = rng.uniform(-2.0, 2.0, size=N)
    noise = rng.normal(0.0, 0.25, size=N)
    y = 1.0 + 3.0 * x + noise

    slope, intercept = np.polyfit(x, y, 1)
    y_hat = slope * x + intercept
    mse = float(np.mean((y - y_hat) ** 2))
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - float(np.mean(y))) ** 2))
    r2 = float(1.0 - ss_res / ss_tot) if ss_tot != 0 else 0.0

    results_base = {
        "meta": {
            "seed": SEED,
            "n": N,
            "numpy_version": np.__version__,
            "matplotlib_version": matplotlib.__version__,
        },
        "model": {"slope": float(slope), "intercept": float(intercept)},
        "metrics": {"mse": mse, "r2": r2},
    }
    results_checksum = sha256_hex(canonical_json_bytes(results_base))
    results = dict(results_base)
    results["results_checksum"] = results_checksum

    RESULTS_PATH.write_text(json.dumps(results, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    fig, ax = plt.subplots(figsize=(6, 4), dpi=150)
    ax.scatter(x, y, s=14, alpha=0.75, color="#1f77b4", edgecolors="none")
    xs = np.linspace(-2.0, 2.0, 200)
    ax.plot(xs, slope * xs + intercept, color="#d62728", linewidth=2.0)
    ax.set_title("Synthetic linear fit (deterministic)")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIG_PATH, format="png", bbox_inches="tight", metadata={"Software": "matplotlib"})
    plt.close(fig)

    figure_dhash = dhash_hex_png(FIG_PATH, hash_size=8)

    baseline = {"results_checksum": results_checksum, "figure_dhash": figure_dhash}
    if BASELINE_PATH.exists():
        prev = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        prev_rc = prev.get("results_checksum")
        prev_fh = prev.get("figure_dhash")
        ok = True
        if prev_rc and prev_rc != results_checksum:
            ok = False
            raise SystemExit(f"STABILITY_FAIL: results_checksum changed {prev_rc} -> {results_checksum}")
        if prev_fh:
            dist = hamming_hex(prev_fh, figure_dhash)
            if dist > 6:
                ok = False
                raise SystemExit(f"STABILITY_FAIL: figure_dhash changed (ham={dist}) {prev_fh} -> {figure_dhash}")
        if ok:
            pass
    else:
        BASELINE_PATH.write_text(json.dumps(baseline, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    return {"results_checksum": results_checksum, "figure_dhash": figure_dhash}


if __name__ == "__main__":
    info = run()
    print("OK", json.dumps(info, sort_keys=True))
