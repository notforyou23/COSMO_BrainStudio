#!/usr/bin/env python3
\"\"\"Benchmark reproduction check.

Runs a benchmark command expected to emit JSON results (dict of name->number) on stdout,
compares against a committed baseline within tolerances, and writes:
- bench_repro_diff.txt (human-readable)
- bench_repro_report.json (machine-readable)
Exit code 0 if within tolerances, else 1.
\"\"\"

from __future__ import annotations

import argparse, json, os, re, subprocess, sys
from pathlib import Path
from typing import Dict, Any, Tuple


def _stable_env() -> dict:
    env = dict(os.environ)
    env.setdefault("PYTHONHASHSEED", "0")
    for k in ("OMP_NUM_THREADS","MKL_NUM_THREADS","OPENBLAS_NUM_THREADS","NUMEXPR_NUM_THREADS"):
        env.setdefault(k, "1")
    env.setdefault("TOKENIZERS_PARALLELISM", "false")
    return env


def _parse_json_from_stdout(stdout: str) -> Dict[str, float]:
    s = stdout.strip()
    if not s:
        raise ValueError("benchmark command produced empty stdout; expected JSON")
    # Try whole stdout first; fallback to last {...} or [...] block.
    try:
        obj = json.loads(s)
    except Exception:
        m = re.findall(r"(\{.*\}|\[.*\])", s, flags=re.S)
        if not m:
            raise
        obj = json.loads(m[-1])
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if isinstance(v, (int, float)):
                out[str(k)] = float(v)
        if not out:
            raise ValueError("parsed JSON dict but found no numeric values")
        return out
    raise ValueError("expected JSON object mapping benchmark->number")


def _load_baseline(path: Path) -> Dict[str, float]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("baseline must be a JSON object mapping benchmark->number")
    return {str(k): float(v) for k, v in obj.items() if isinstance(v, (int, float))}


def _compare(baseline: Dict[str, float], current: Dict[str, float], rel: float, abs_: float):
    all_keys = sorted(set(baseline) | set(current))
    rows = []
    ok = True
    for k in all_keys:
        b = baseline.get(k)
        c = current.get(k)
        if b is None or c is None:
            ok = False
            rows.append((k, b, c, None, None, False, "missing"))
            continue
        delta = c - b
        tol = abs_ + rel * (abs(b) if b != 0 else 1.0)
        passed = abs(delta) <= tol
        ok &= passed
        pct = None if b == 0 else (delta / b) * 100.0
        rows.append((k, b, c, delta, pct, passed, f"tol={tol:g}"))
    return ok, rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cmd", default="python -m benchmarks.run", help="benchmark command (shell-like)")
    ap.add_argument("--baseline", default="benchmarks/baseline.json")
    ap.add_argument("--out-dir", default="artifacts/bench_repro")
    ap.add_argument("--rel-tol", type=float, default=0.05, help="relative tolerance (fraction)")
    ap.add_argument("--abs-tol", type=float, default=0.0, help="absolute tolerance")
    args = ap.parse_args(argv)

    baseline_path = Path(args.baseline)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    report = {"cmd": args.cmd, "baseline": str(baseline_path), "rel_tol": args.rel_tol, "abs_tol": args.abs_tol}

    try:
        baseline = _load_baseline(baseline_path)
        report["baseline_count"] = len(baseline)
    except Exception as e:
        (out_dir / "bench_repro_diff.txt").write_text(f"ERROR loading baseline: {e}\n", encoding="utf-8")
        report.update({"status": "error", "error": f"baseline: {e}"})
        (out_dir / "bench_repro_report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        return 2

    try:
        p = subprocess.run(args.cmd, shell=True, check=False, text=True, capture_output=True, env=_stable_env())
        (out_dir / "bench_stdout.txt").write_text(p.stdout, encoding="utf-8")
        (out_dir / "bench_stderr.txt").write_text(p.stderr, encoding="utf-8")
        report.update({"returncode": p.returncode})
        if p.returncode != 0:
            raise RuntimeError(f"benchmark command failed with rc={p.returncode}")
        current = _parse_json_from_stdout(p.stdout)
        report["current_count"] = len(current)
    except Exception as e:
        (out_dir / "bench_repro_diff.txt").write_text(f"ERROR running/parsing benchmarks: {e}\n", encoding="utf-8")
        report.update({"status": "error", "error": f"run/parse: {e}"})
        (out_dir / "bench_repro_report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        return 2

    ok, rows = _compare(baseline, current, args.rel_tol, args.abs_tol)
    lines = [f"Benchmark reproduction check: {'PASS' if ok else 'FAIL'}",
             f"cmd: {args.cmd}",
             f"baseline: {baseline_path}",
             f"tolerances: rel={args.rel_tol} abs={args.abs_tol}",
             ""]
    fmt = "{:<40} {:>12} {:>12} {:>12} {:>10} {:>7}  {}"
    lines.append(fmt.format("name","baseline","current","delta","pct","pass","note"))
    for k,b,c,d,pct,passed,note in rows:
        sb = "NA" if b is None else f"{b:.6g}"
        sc = "NA" if c is None else f"{c:.6g}"
        sd = "NA" if d is None else f"{d:.6g}"
        sp = "NA" if pct is None else f"{pct:.2f}%"
        lines.append(fmt.format(k[:40], sb, sc, sd, sp, "yes" if passed else "NO", note))
    (out_dir / "bench_repro_diff.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    report.update({
        "status": "pass" if ok else "fail",
        "results": {k: {"baseline": b, "current": c, "delta": d, "pct": pct, "pass": passed, "note": note}
                    for k,b,c,d,pct,passed,note in rows},
    })
    (out_dir / "bench_repro_report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
