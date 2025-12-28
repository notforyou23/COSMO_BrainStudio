#!/usr/bin/env python3
import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path

def _run(cmd, *, cwd: Path, env=None) -> None:
    if isinstance(cmd, str):
        cmd_list = shlex.split(cmd)
    else:
        cmd_list = list(cmd)
    p = subprocess.run(cmd_list, cwd=str(cwd), env=env)
    if p.returncode != 0:
        raise SystemExit(p.returncode)

def _maybe_run_py(cwd: Path, rel_py: str, *, args=None) -> None:
    p = cwd / rel_py
    if p.is_file():
        _run([sys.executable, str(p)] + (args or []), cwd=cwd)

def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(prog="run.py", description="One-command runner")
    ap.add_argument("--cwd", default=None, help="Project root (defaults to scripts/..)")
    ap.add_argument("--no-default-steps", action="store_true", help="Skip default build/validate steps")
    ap.add_argument("--", dest="passthrough", nargs=argparse.REMAINDER, help="Args forwarded to gate/verify_artifacts.py")
    ns = ap.parse_args(argv)

    root = Path(ns.cwd).resolve() if ns.cwd else Path(__file__).resolve().parents[1]
    env = os.environ.copy()

    if not ns.no_default_steps:
        # Best-effort: run common steps if present; missing files are skipped.
        _maybe_run_py(root, "scripts/build.py")
        _maybe_run_py(root, "scripts/validate.py")
        _maybe_run_py(root, "scripts/check.py")
        _maybe_run_py(root, "scripts/report.py")

    gate = root / "gate" / "verify_artifacts.py"
    if not gate.is_file():
        sys.stderr.write(f"ERROR: Missing required gate script: {gate}\n")
        return 2

    gate_args = []
    if ns.passthrough:
        gate_args = ns.passthrough[1:] if ns.passthrough and ns.passthrough[0] == "--" else ns.passthrough
    _run([sys.executable, str(gate)] + gate_args, cwd=root, env=env)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
