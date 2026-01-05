#!/usr/bin/env python3
from __future__ import annotations

import os
import shlex
import sys
import time
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "runtime" / "_build" / "logs"

STEPS = [
    {
        "name": "taxonomy_smoke_test",
        "title": "1) taxonomy smoke-test",
        "env": "TAXONOMY_SMOKE_TEST_CMD",
        "candidates": [
            "python -m taxonomy_smoke_test",
            "python taxonomy_smoke_test.py",
            "python scripts/taxonomy_smoke_test.py",
            "python tests/taxonomy_smoke_test.py",
            "python -m tests.taxonomy_smoke_test",
            "python -m scripts.taxonomy_smoke_test",
            "python -m taxonomy.smoke_test",
            "python -m taxonomy.smoke",
        ],
    },
    {
        "name": "toy_demo_run",
        "title": "2) toy demo run",
        "env": "TOY_DEMO_CMD",
        "candidates": [
            "python toy_demo.py",
            "python demo.py",
            "python scripts/toy_demo.py",
            "python scripts/demo.py",
            "python -m toy_demo",
            "python -m demo",
            "python -m scripts.toy_demo",
            "python -m scripts.demo",
        ],
    },
    {
        "name": "artifact_gate",
        "title": "3) artifact gate",
        "env": "ARTIFACT_GATE_CMD",
        "candidates": [
            "python artifact_gate.py",
            "python scripts/artifact_gate.py",
            "python -m artifact_gate",
            "python -m scripts.artifact_gate",
            "python -m gate.artifact_gate",
        ],
    },
]


def _split_cmd(cmd: str) -> list[str]:
    return shlex.split(cmd, posix=(os.name != "nt"))


def _cmd_exists(cmd: str) -> bool:
    parts = _split_cmd(cmd)
    if not parts:
        return False
    exe = parts[0].lower()
    if exe in {"python", "python3", sys.executable.lower()}:
        if len(parts) < 2:
            return False
        if parts[1] == "-m" and len(parts) >= 3:
            return True
        return (ROOT / parts[1]).exists()
    if (ROOT / parts[0]).exists():
        return True
    return False


def choose_cmd(step: dict) -> str:
    override = os.environ.get(step["env"], "").strip()
    if override:
        return override
    for cand in step["candidates"]:
        if _cmd_exists(cand):
            return cand
    return step["candidates"][0]


def tee_process(cmd: str, log_path: Path) -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with log_path.open("w", encoding="utf-8") as lf:
        lf.write(f"CMD: {cmd}\nCWD: {ROOT}\nSTART: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        lf.flush()
        proc = subprocess.Popen(
            _split_cmd(cmd),
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            lf.write(line)
        rc = proc.wait()
        dt = time.time() - t0
        lf.write(f"\nEXIT_CODE: {rc}\nDURATION_SEC: {dt:.3f}\nEND: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        lf.flush()
        return rc


def main(argv: list[str]) -> int:
    if "--help" in argv or "-h" in argv:
        print("Usage: python run_all.py [--list]\nEnv overrides: TAXONOMY_SMOKE_TEST_CMD, TOY_DEMO_CMD, ARTIFACT_GATE_CMD")
        return 0
    if "--list" in argv:
        for s in STEPS:
            print(f"{s['name']}: {choose_cmd(s)}")
        return 0

    for step in STEPS:
        cmd = choose_cmd(step)
        log_path = LOG_DIR / f"{step['name']}.log"
        print(f"\n==> {step['title']} :: {cmd}\n    log: {log_path}")
        rc = tee_process(cmd, log_path)
        if rc != 0:
            print(f"\nFAILED: {step['name']} (exit {rc}); see log: {log_path}", file=sys.stderr)
            return rc
        print(f"DONE: {step['name']}")
    print("\nALL DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
