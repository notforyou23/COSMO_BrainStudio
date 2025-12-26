#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def first_existing(paths) -> Path | None:
    for p in paths:
        if p.is_file():
            return p
    return None


def find_benchmark_input(root: Path) -> Path:
    candidates = [
        root / "examples" / "benchmark_case_001.json",
        root / "examples" / "benchmark_case_001" / "input.json",
    ]
    p = first_existing(candidates)
    if p is not None:
        return p
    hits = sorted(
        x for x in root.rglob("benchmark_case_001*.json")
        if x.is_file() and "expected" not in x.name.lower()
    )
    if hits:
        return hits[0]
    raise FileNotFoundError("benchmark_case_001 input JSON not found (looked under examples/ and repo-wide).")


def find_reference_script(root: Path) -> Path:
    patterns = ["generated_script_*.py", "src/**/main.py", "main.py", "run.py"]
    for pat in patterns:
        hits = sorted(root.rglob(pat))
        if hits:
            return hits[0]
    raise FileNotFoundError("Reference implementation script not found (e.g., generated_script_*.py).")


def run_reference(script: Path, input_path: Path, output_dir: Path) -> None:
    cmd = [sys.executable, str(script), "--input", str(input_path), "--output", str(output_dir)]
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    proc = subprocess.run(cmd, cwd=str(repo_root()), env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(
            "Reference run failed.\n"
            f"CMD: {' '.join(cmd)}\n"
            f"STDOUT:\n{proc.stdout}\n"
            f"STDERR:\n{proc.stderr}\n"
        )
    # Keep CI logs short; print stderr only if present.
    if proc.stderr.strip():
        print(proc.stderr.rstrip())


def main() -> int:
    root = repo_root()
    ap = argparse.ArgumentParser(description="CI helper: run benchmark_case_001 and write outputs for upload.")
    ap.add_argument("--artifacts-dir", default=os.environ.get("BENCHMARK_OUTPUT_DIR", "ci_outputs"))
    ap.add_argument("--case-name", default="benchmark_case_001")
    ap.add_argument("--clean", action="store_true", help="Delete existing output dir before running.")
    args = ap.parse_args()

    artifacts_dir = Path(args.artifacts_dir)
    if not artifacts_dir.is_absolute():
        artifacts_dir = root / artifacts_dir
    out_dir = artifacts_dir / args.case_name

    if args.clean and out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    input_path = find_benchmark_input(root)
    script = find_reference_script(root)

    print(f"RUN: script={script.relative_to(root)} input={input_path.relative_to(root)} out={out_dir.relative_to(root)}")
    run_reference(script, input_path, out_dir)

    produced = sorted(out_dir.rglob("*"))
    files = [p for p in produced if p.is_file()]
    if not files:
        raise SystemExit(f"No outputs produced under {out_dir}")
    print(f"OK: produced_files={len(files)}")
    # Print a small sample of file names for quick inspection in logs.
    for p in files[:20]:
        print(f"  - {p.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
