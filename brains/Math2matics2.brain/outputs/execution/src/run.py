import argparse
import hashlib
import json
import os
import random
import sys
import tempfile
from pathlib import Path

import numpy as np


def set_all_seeds(seed: int) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch  # type: ignore

        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
        try:
            torch.use_deterministic_algorithms(True)
        except Exception:
            pass
    except Exception:
        pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    atomic_write_bytes(path, text.encode(encoding))


def stable_json_dumps(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n"


def run_pipeline(seed: int, n: int = 200, degree: int = 3):
    rng = np.random.default_rng(seed)
    x = np.linspace(0.0, 1.0, n, dtype=np.float64)
    y = np.sin(2.0 * np.pi * x) + rng.normal(0.0, 0.1, size=n)
    coefs = np.polyfit(x, y, deg=degree)
    yhat = np.polyval(coefs, x)

    resid = y - yhat
    mse = float(np.mean(resid ** 2))
    mae = float(np.mean(np.abs(resid)))
    sst = float(np.sum((y - float(np.mean(y))) ** 2))
    ssr = float(np.sum((y - yhat) ** 2))
    r2 = float(1.0 - ssr / sst) if sst > 0 else 0.0

    results = {
        "schema_version": 1,
        "seed": int(seed),
        "data": {"n": int(n), "x_min": float(x.min()), "x_max": float(x.max()), "noise_std": 0.1},
        "model": {"type": "polynomial_regression", "degree": int(degree), "coefficients": [float(c) for c in coefs]},
        "metrics": {"mse": mse, "mae": mae, "r2": r2},
    }
    fig_payload = {"x": x, "y": y, "yhat": yhat, "degree": degree}
    return results, fig_payload


def save_figure(fig_path: Path, payload) -> None:
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt  # noqa: E402

    x, y, yhat = payload["x"], payload["y"], payload["yhat"]
    fig, ax = plt.subplots(figsize=(7, 4), dpi=160)
    ax.scatter(x, y, s=10, alpha=0.7, label="data")
    ax.plot(x, yhat, linewidth=2.0, label="fit")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_title(f"Deterministic polynomial fit (degree={payload['degree']})")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.25)

    fig_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=fig_path.name + ".", suffix=".tmp", dir=str(fig_path.parent))
    os.close(fd)
    try:
        fig.savefig(tmp, format="png", bbox_inches="tight")
        plt.close(fig)
        os.replace(tmp, fig_path)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Deterministic canonical pipeline runner")
    p.add_argument("--seed", type=int, default=12345, help="Random seed (default: 12345)")
    args = p.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    out_dir = root / "outputs"
    results_path = out_dir / "results.json"
    fig_path = out_dir / "figure.png"
    hashes_path = out_dir / "hashes.json"

    set_all_seeds(args.seed)
    results, fig_payload = run_pipeline(args.seed)

    atomic_write_text(results_path, stable_json_dumps(results))
    save_figure(fig_path, fig_payload)

    hashes = {
        "schema_version": 1,
        "artifacts": {
            "results.json": {"path": str(results_path.as_posix()), "sha256": sha256_file(results_path)},
            "figure.png": {"path": str(fig_path.as_posix()), "sha256": sha256_file(fig_path)},
        },
    }
    atomic_write_text(hashes_path, stable_json_dumps(hashes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
