#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_toy_experiment(outputs: Path, seed: int, n: int) -> dict:
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        x = i
        y = rng.random() * 2 - 1
        rows.append({"i": i, "x": x, "y": y})

    ys = [r["y"] for r in rows]
    mean_y = sum(ys) / len(ys)
    min_y = min(ys)
    max_y = max(ys)

    data_json = outputs / "data.json"
    results_json = outputs / "results.json"
    sample_csv = outputs / "sample.csv"
    ascii_plot = outputs / "plot.txt"

    write_text(data_json, json.dumps({"seed": seed, "n": n, "rows": rows}, indent=2, sort_keys=True) + "\n")
    write_text(results_json, json.dumps({"mean_y": mean_y, "min_y": min_y, "max_y": max_y}, indent=2, sort_keys=True) + "\n")

    with sample_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["i", "x", "y"])
        w.writeheader()
        for r in rows[: min(25, n)]:
            w.writerow(r)

    # Deterministic tiny ascii plot of y values
    width = 41
    lines = ["Toy ASCII plot of y in [-1, 1] (seed=%d, n=%d)" % (seed, n), ""]
    for r in rows[: min(60, n)]:
        y = max(-1.0, min(1.0, float(r["y"])))
        pos = int(round((y + 1.0) * (width - 1) / 2.0))
        line = [" "] * width
        mid = (width - 1) // 2
        line[mid] = "|"
        line[pos] = "*"
        lines.append(f'{r["i"]:03d} ' + "".join(line) + f"  y={y:+.6f}")
    write_text(ascii_plot, "\n".join(lines) + "\n")

    return {
        "artifacts": [data_json, results_json, sample_csv, ascii_plot],
        "metrics": {"mean_y": mean_y, "min_y": min_y, "max_y": max_y},
    }


def write_manifest(outputs: Path, meta: dict, artifacts: list[Path]) -> Path:
    idx = outputs / "index.md"
    rel = lambda p: p.relative_to(outputs).as_posix()
    lines = [
        "# Pipeline Outputs",
        "",
        f"- Generated (UTC): `{meta['generated_utc']}`",
        f"- Host: `{meta['host']}`",
        f"- Python: `{meta['python']}`",
        f"- Seed: `{meta['seed']}`",
        f"- N: `{meta['n']}`",
        "",
        "## Artifacts",
        "",
        "| file | bytes | sha256 |",
        "|---|---:|---|",
    ]
    for p in artifacts + [idx]:
        if not p.exists():
            continue
        lines.append(f"| `{rel(p)}` | {p.stat().st_size} | `{sha256_file(p)}` |")
    write_text(idx, "\n".join(lines) + "\n")
    return idx


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Single entrypoint pipeline: creates outputs/, runs toy experiment, writes outputs/index.md.")
    ap.add_argument("--seed", type=int, default=0, help="Deterministic RNG seed (default: 0)")
    ap.add_argument("--n", type=int, default=200, help="Number of samples (default: 200)")
    args = ap.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    outputs = root / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)

    try:
        run = run_toy_experiment(outputs=outputs, seed=args.seed, n=args.n)
        artifacts = list(run["artifacts"])
        meta = {
            "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "host": os.uname().nodename if hasattr(os, "uname") else "unknown",
            "python": sys.version.split()[0],
            "seed": args.seed,
            "n": args.n,
        }
        index_path = write_manifest(outputs, meta, artifacts)
        expected = artifacts + [index_path]
        missing = [p for p in expected if not p.exists()]
        if missing:
            print("ERROR: missing expected outputs: " + ", ".join(str(p) for p in missing), file=sys.stderr)
            return 2
        return 0
    except Exception as e:
        print(f"ERROR: pipeline failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
