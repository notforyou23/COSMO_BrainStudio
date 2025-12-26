#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, platform, sys, time
from pathlib import Path

def _stable_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n"

def _write_text(path: Path, text: str, overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite: {path}")
    path.write_text(text, encoding="utf-8", newline="\n")

def _write_bytes(path: Path, data: bytes, overwrite: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite: {path}")
    path.write_bytes(data)

def _source_date_epoch() -> int:
    v = os.environ.get("SOURCE_DATE_EPOCH", "")
    try:
        return int(v)
    except Exception:
        return 0

def compute(seed: int, n: int) -> dict:
    xs = list(range(n))
    ys = [((seed * 1103515245 + 12345 + i * 2654435761) & 0xFFFFFFFF) / 2**32 for i in xs]
    mean = sum(ys) / n if n else 0.0
    var = (sum((y - mean) ** 2 for y in ys) / n) if n else 0.0
    return {"seed": seed, "n": n, "x": xs, "y": ys, "summary": {"mean": mean, "variance": var}}

def make_figure_png(results: dict) -> bytes:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "figure.figsize": (6.4, 4.8),
        "figure.dpi": 100,
        "savefig.dpi": 100,
        "font.size": 10,
        "axes.grid": True,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "legend.fontsize": 9,
    })
    fig, ax = plt.subplots()
    ax.plot(results["x"], results["y"], color="#1f77b4", linewidth=1.5, label="y")
    ax.set_title("Deterministic Series")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.legend(loc="best", frameon=False)
    import io
    buf = io.BytesIO()
    fig.savefig(buf, format="png", metadata={}, bbox_inches=None)
    plt.close(fig)
    return buf.getvalue()

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="run.py", description="Deterministic pipeline writing required /outputs artifacts.")
    ap.add_argument("--outdir", default="outputs", help="Output directory (relative to repo root).")
    ap.add_argument("--seed", type=int, default=123, help="Deterministic seed.")
    ap.add_argument("--n", type=int, default=50, help="Number of points.")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing artifacts (default).")
    ap.add_argument("--no-overwrite", dest="overwrite", action="store_false", help="Refuse to overwrite existing artifacts.")
    ap.set_defaults(overwrite=True)
    args = ap.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[1]
    outdir = (repo_root / args.outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    started_epoch = _source_date_epoch()
    results = compute(args.seed, args.n)
    results_text = _stable_json(results)
    results_hash = hashlib.sha256(results_text.encode("utf-8")).hexdigest()

    run_stamp = {
        "schema_version": 1,
        "run_id": hashlib.sha256(f"{args.seed}:{args.n}:{results_hash}".encode("utf-8")).hexdigest()[:16],
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started_epoch)),
        "config": {"seed": args.seed, "n": args.n, "outdir": str(Path(args.outdir))},
        "artifacts": {
            "run_stamp_json": "run_stamp.json",
            "run_log": "run.log",
            "results_json": "results.json",
            "figure_png": "figure.png",
        },
        "results_sha256": results_hash,
        "environment": {"python": sys.version.split()[0], "platform": platform.platform()},
        "determinism": {
            "source_date_epoch": started_epoch,
            "json_sorted_keys": True,
            "png_metadata_stripped": True,
            "overwrite_policy": "overwrite" if args.overwrite else "refuse",
        },
    }

    log_lines = [
        "pipeline=deterministic_cli_v1",
        f"outdir={outdir.as_posix()}",
        f"seed={args.seed}",
        f"n={args.n}",
        f"started_utc={run_stamp['started_utc']}",
        f"results_sha256={results_hash}",
        f"overwrite_policy={'overwrite' if args.overwrite else 'refuse'}",
    ]
    log_text = "\n".join(log_lines) + "\n"

    _write_text(outdir / "results.json", results_text, args.overwrite)
    _write_text(outdir / "run_stamp.json", _stable_json(run_stamp), args.overwrite)
    _write_text(outdir / "run.log", log_text, args.overwrite)
    _write_bytes(outdir / "figure.png", make_figure_png(results), args.overwrite)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
