"""Single-command meta-analysis pipeline.

Usage:
  python -m src.run_pipeline [path/to/run_config.json]

If the config or input CSV is missing, a toy dataset + default config are created
to enable deterministic end-to-end execution.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_REL = Path("config/run_config.json")
DEFAULT_DATA_REL = Path("data/toy_extraction.csv")


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _json_dump(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def _write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})
    os.replace(tmp, path)


def _ensure_default_files(config_path: Path) -> Dict[str, Any]:
    default_cfg = {
        "input_csv": str(DEFAULT_DATA_REL),
        "build_dir": "runtime/_build",
        "effect_col": "yi",
        "se_col": "sei",
        "study_id_col": "study_id",
        "model": {"fixed": True, "random": True},
        "exports": {
            "pooled_csv": "pooled_estimates.csv",
            "pooled_json": "pooled_estimates.json",
            "plot": {"file": "forest_plot.png", "dpi": 200}
        },
    }
    if not config_path.exists():
        _atomic_write(config_path, _json_dump(default_cfg))

    data_path = ROOT / Path(default_cfg["input_csv"])
    if not data_path.exists():
        data_path.parent.mkdir(parents=True, exist_ok=True)
        rows = [
            {"study_id": "Study_A", "yi": 0.20, "sei": 0.10, "n_treat": 50, "n_ctrl": 50, "outcome": "toy"},
            {"study_id": "Study_B", "yi": 0.35, "sei": 0.12, "n_treat": 40, "n_ctrl": 42, "outcome": "toy"},
            {"study_id": "Study_C", "yi": 0.05, "sei": 0.08, "n_treat": 60, "n_ctrl": 61, "outcome": "toy"},
            {"study_id": "Study_D", "yi": 0.40, "sei": 0.15, "n_treat": 30, "n_ctrl": 30, "outcome": "toy"},
            {"study_id": "Study_E", "yi": 0.18, "sei": 0.09, "n_treat": 55, "n_ctrl": 54, "outcome": "toy"},
        ]
        _write_csv(data_path, rows, ["study_id", "yi", "sei", "n_treat", "n_ctrl", "outcome"])

    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)


@dataclass
class MetaResult:
    model: str
    k: int
    estimate: float
    se: float
    ci_low: float
    ci_high: float
    tau2: float | None
    i2: float | None
    q: float | None


def _read_extraction_csv(path: Path, study_id_col: str, effect_col: str, se_col: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for i, r in enumerate(reader, start=1):
            if not r:
                continue
            try:
                sid = (r.get(study_id_col) or f"Study_{i}").strip()
                yi = float(r[effect_col])
                sei = float(r[se_col])
            except Exception:
                continue
            if not (math.isfinite(yi) and math.isfinite(sei) and sei > 0):
                continue
            r2 = dict(r)
            r2[study_id_col] = sid
            r2[effect_col] = yi
            r2[se_col] = sei
            rows.append(r2)
    if not rows:
        raise ValueError(f"No valid rows found in extraction CSV: {path}")
    return rows


def _meta_fixed(yi: List[float], vi: List[float]) -> Tuple[float, float, float]:
    wi = [1.0 / v for v in vi]
    sw = sum(wi)
    mu = sum(w * y for w, y in zip(wi, yi)) / sw
    se = math.sqrt(1.0 / sw)
    q = sum(w * (y - mu) ** 2 for w, y in zip(wi, yi))
    return mu, se, q


def _meta_random_dl(yi: List[float], vi: List[float]) -> Tuple[float, float, float, float, float]:
    k = len(yi)
    mu_fe, _, q = _meta_fixed(yi, vi)
    wi = [1.0 / v for v in vi]
    sw = sum(wi)
    sw2 = sum(w * w for w in wi)
    c = sw - (sw2 / sw)
    tau2 = max(0.0, (q - (k - 1)) / c) if c > 0 else 0.0
    wi_re = [1.0 / (v + tau2) for v in vi]
    sw_re = sum(wi_re)
    mu = sum(w * y for w, y in zip(wi_re, yi)) / sw_re
    se = math.sqrt(1.0 / sw_re)
    i2 = max(0.0, (q - (k - 1)) / q) * 100.0 if q > 0 else 0.0
    return mu, se, tau2, q, i2


def _z_ci(est: float, se: float, z: float = 1.96) -> Tuple[float, float]:
    return est - z * se, est + z * se


def _format_float(x: Any) -> Any:
    if x is None:
        return None
    try:
        xf = float(x)
    except Exception:
        return x
    if not math.isfinite(xf):
        return None
    return float(f"{xf:.6g}")


def _to_export_rows(results: List[MetaResult]) -> List[Dict[str, Any]]:
    out = []
    for r in results:
        out.append({
            "model": r.model,
            "k": r.k,
            "estimate": _format_float(r.estimate),
            "se": _format_float(r.se),
            "ci_low": _format_float(r.ci_low),
            "ci_high": _format_float(r.ci_high),
            "tau2": _format_float(r.tau2),
            "i2_percent": _format_float(r.i2),
            "q": _format_float(r.q),
        })
    return out


def _forest_plot(studies: List[Dict[str, Any]], study_id_col: str, effect_col: str, se_col: str,
                 pooled: Dict[str, float], out_path: Path, dpi: int = 200) -> None:
    sids = [str(r[study_id_col]) for r in studies]
    yi = [float(r[effect_col]) for r in studies]
    sei = [float(r[se_col]) for r in studies]
    ci = [(_z_ci(y, s)) for y, s in zip(yi, sei)]

    k = len(yi)
    fig_h = max(2.5, 0.35 * k + 1.5)
    fig, ax = plt.subplots(figsize=(7.5, fig_h))
    y_pos = list(range(k, 0, -1))

    for yp, y, (lo, hi) in zip(y_pos, yi, ci):
        ax.plot([lo, hi], [yp, yp], color="black", lw=1)
        ax.plot([y], [yp], marker="s", color="black", ms=4)

    ax.axvline(0.0, color="gray", lw=1, ls="--")
    if pooled:
        pe, pcl, pch = pooled["estimate"], pooled["ci_low"], pooled["ci_high"]
        ax.plot([pcl, pch], [0, 0], color="tab:blue", lw=2)
        ax.plot([pe], [0], marker="D", color="tab:blue", ms=6)

    ax.set_yticks(y_pos + [0])
    ax.set_yticklabels(sids + ["Pooled"])
    ax.set_xlabel("Effect (yi) with 95% CI")
    ax.set_ylim(-1, k + 1)
    ax.grid(axis="x", color="0.9", lw=0.8)
    ax.set_title("Forest plot (toy meta-analysis)")
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=dpi)
    plt.close(fig)


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("config", nargs="?", default=str(DEFAULT_CONFIG_REL), help="Path to run_config.json")
    args = ap.parse_args(argv)

    config_path = (ROOT / Path(args.config)).resolve()
    cfg = _ensure_default_files(config_path)

    input_csv = (ROOT / Path(cfg["input_csv"])).resolve()
    build_dir = (ROOT / Path(cfg.get("build_dir", "runtime/_build"))).resolve()
    build_dir.mkdir(parents=True, exist_ok=True)

    study_id_col = cfg.get("study_id_col", "study_id")
    effect_col = cfg.get("effect_col", "yi")
    se_col = cfg.get("se_col", "sei")

    t0 = time.time()
    studies = _read_extraction_csv(input_csv, study_id_col, effect_col, se_col)
    yi = [float(r[effect_col]) for r in studies]
    vi = [float(r[se_col]) ** 2 for r in studies]
    k = len(yi)

    results: List[MetaResult] = []
    if cfg.get("model", {}).get("fixed", True):
        mu, se, q = _meta_fixed(yi, vi)
        lo, hi = _z_ci(mu, se)
        i2 = max(0.0, (q - (k - 1)) / q) * 100.0 if q > 0 else 0.0
        results.append(MetaResult("fixed", k, mu, se, lo, hi, None, i2, q))
    if cfg.get("model", {}).get("random", True):
        mu, se, tau2, q, i2 = _meta_random_dl(yi, vi)
        lo, hi = _z_ci(mu, se)
        results.append(MetaResult("random_DL", k, mu, se, lo, hi, tau2, i2, q))

    export_rows = _to_export_rows(results)
    exports = cfg.get("exports", {})
    pooled_csv = build_dir / exports.get("pooled_csv", "pooled_estimates.csv")
    pooled_json = build_dir / exports.get("pooled_json", "pooled_estimates.json")
    _write_csv(pooled_csv, export_rows, ["model", "k", "estimate", "se", "ci_low", "ci_high", "tau2", "i2_percent", "q"])
    _atomic_write(pooled_json, _json_dump(export_rows))

    plot_cfg = (exports.get("plot") or {})
    plot_path = build_dir / str(plot_cfg.get("file", "forest_plot.png"))
    pooled_for_plot = next((r for r in export_rows if r["model"] != "fixed"), None) or export_rows[0]
    pooled_dict = {
        "estimate": float(pooled_for_plot["estimate"]),
        "ci_low": float(pooled_for_plot["ci_low"]),
        "ci_high": float(pooled_for_plot["ci_high"]),
    }
    _forest_plot(studies, study_id_col, effect_col, se_col, pooled_dict, plot_path, dpi=int(plot_cfg.get("dpi", 200)))

    log = {
        "started_at_unix": t0,
        "finished_at_unix": time.time(),
        "duration_sec": round(time.time() - t0, 6),
        "cwd": str(Path.cwd()),
        "root": str(ROOT),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "config_path": str(config_path),
        "input_csv": str(input_csv),
        "build_dir": str(build_dir),
        "inputs": {"config_sha256": _sha256(config_path), "csv_sha256": _sha256(input_csv)},
        "outputs": {
            "pooled_csv": str(pooled_csv),
            "pooled_json": str(pooled_json),
            "plot": str(plot_path),
        },
        "params": {"study_id_col": study_id_col, "effect_col": effect_col, "se_col": se_col, "k": k},
    }
    _atomic_write(build_dir / "run_log.json", _json_dump(log))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
