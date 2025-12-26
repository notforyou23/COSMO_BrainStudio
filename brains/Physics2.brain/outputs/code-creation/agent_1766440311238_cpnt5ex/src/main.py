#!/usr/bin/env python3
"""CLI entry point for small numerical/symbolic prototype experiments.

Runs one or more built-in experiments, writes artifacts under --outdir, and prints a
short summary suitable for reproducing results.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple
def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, header: Iterable[str], rows: Iterable[Iterable[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(list(header))
        for r in rows:
            w.writerow(list(r))


def _env_info() -> Dict[str, Any]:
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "executable": sys.executable,
        "cwd": os.getcwd(),
    }
def exp_logistic_map(outdir: Path, seed: int, steps: int, r: float) -> Dict[str, Any]:
    """Chaotic map x_{n+1} = r x_n (1-x_n); illustrates sensitivity to initial conditions."""
    random.seed(seed)
    x0 = 0.123456 + (random.random() - 0.5) * 1e-6
    x = x0
    xs: List[float] = []
    for _ in range(steps):
        x = r * x * (1.0 - x)
        xs.append(float(x))
    burn = min(100, len(xs))
    tail = xs[burn:] if burn < len(xs) else xs
    mean = sum(tail) / max(1, len(tail))
    var = sum((v - mean) ** 2 for v in tail) / max(1, len(tail))
    csv_path = outdir / "logistic_map.csv"
    _write_csv(csv_path, ["n", "x"], ((i, v) for i, v in enumerate(xs)))
    meta = {"x0": x0, "r": r, "steps": steps, "tail_mean": mean, "tail_std": math.sqrt(var)}
    _write_json(outdir / "logistic_map.json", meta)
    return {"name": "logistic_map", "artifacts": [str(csv_path.name), "logistic_map.json"], "metrics": meta}
def exp_sympy_series(outdir: Path, order: int) -> Dict[str, Any]:
    """Symbolic Taylor series + simplification to show exact vs numeric agreement."""
    try:
        import sympy as sp
    except Exception as e:  # pragma: no cover
        raise SystemExit(f"sympy is required for 'sympy_series' experiment: {e}") from e
    x = sp.Symbol("x")
    expr = sp.sin(x) / (1 + x)
    series = sp.series(expr, x, 0, order).removeO()
    simplified = sp.simplify(series)
    poly = sp.Poly(simplified, x)
    coeffs = [float(poly.nth(i)) for i in range(order)]
    rows = [(i, str(poly.nth(i)), coeffs[i]) for i in range(order)]
    _write_csv(outdir / "sympy_series.csv", ["power", "exact_coeff", "float_coeff"], rows)
    _write_json(outdir / "sympy_series.json", {"expr": str(expr), "order": order, "series": str(simplified)})
    return {"name": "sympy_series", "artifacts": ["sympy_series.csv", "sympy_series.json"], "metrics": {"order": order}}
EXPERIMENTS = {
    "logistic_map": exp_logistic_map,
    "sympy_series": exp_sympy_series,
}


def _parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="experiments", description=__doc__)
    p.add_argument("-e", "--experiment", action="append", choices=sorted(EXPERIMENTS), help="Experiment to run (repeatable).")
    p.add_argument("--outdir", default="runs", help="Base output directory.")
    p.add_argument("--seed", type=int, default=0, help="Random seed (when applicable).")
    p.add_argument("--steps", type=int, default=2000, help="Steps for logistic_map.")
    p.add_argument("--r", type=float, default=3.99, help="Parameter r for logistic_map.")
    p.add_argument("--order", type=int, default=10, help="Series order for sympy_series.")
    return p.parse_args(argv)
def main(argv: List[str] | None = None) -> int:
    ns = _parse_args(sys.argv[1:] if argv is None else argv)
    chosen = ns.experiment or ["logistic_map"]
    config = {
        "experiments": chosen,
        "seed": ns.seed,
        "steps": ns.steps,
        "r": ns.r,
        "order": ns.order,
    }
    run_key = _sha256_text(json.dumps(config, sort_keys=True))
    ts = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    run_dir = Path(ns.outdir) / f"{ts}-{run_key}"
    run_dir.mkdir(parents=True, exist_ok=True)

    results: Dict[str, Any] = {"config": config, "env": _env_info(), "run_dir": str(run_dir), "results": []}
    for name in chosen:
        exp_out = run_dir / name
        if name == "logistic_map":
            r = exp_logistic_map(exp_out, seed=ns.seed, steps=ns.steps, r=ns.r)
        elif name == "sympy_series":
            r = exp_sympy_series(exp_out, order=ns.order)
        else:  # pragma: no cover
            raise SystemExit(f"Unknown experiment: {name}")
        results["results"].append(r)

    _write_json(run_dir / "run.json", results)

    # Concise stdout summary
    print(f"RUN_DIR:{run_dir}")
    for r in results["results"]:
        m = r.get("metrics", {})
        if r["name"] == "logistic_map":
            print(f"EXP:{r['name']} r={m['r']} steps={m['steps']} tail_std={m['tail_std']:.6g} artifacts={','.join(r['artifacts'])}")
        else:
            print(f"EXP:{r['name']} order={m.get('order')} artifacts={','.join(r['artifacts'])}")
    print("MANIFEST:run.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
