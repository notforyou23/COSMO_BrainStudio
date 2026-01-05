#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


def _ts() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _rel(root: Path, p: Path) -> str:
    try:
        return str(p.resolve().relative_to(root.resolve()))
    except Exception:
        return str(p)


def _write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _select_command(root: Path, candidates: List[List[str]]) -> List[str]:
    for cmd in candidates:
        if not cmd:
            continue
        if cmd[0] == "{py}":
            if len(cmd) >= 2:
                script = root / cmd[1]
                if script.is_file():
                    return [sys.executable, str(script), *cmd[2:]]
        elif cmd[0] == "{bin}":
            if len(cmd) >= 2 and shutil.which(cmd[1]):
                return [cmd[1], *cmd[2:]]
        elif cmd[0] == "{mod}":
            if len(cmd) >= 2:
                return [sys.executable, "-m", cmd[1], *cmd[2:]]
        else:
            if shutil.which(cmd[0]):
                return cmd
    return []


def _tee_run(cmd: List[str], cwd: Path, env: dict, log_file: Path, prefix: str) -> int:
    _ensure_dir(log_file.parent)
    with log_file.open("a", encoding="utf-8") as f:
        header = f"[{_ts()}] START {prefix} cmd={cmd} cwd={cwd}\n"
        f.write(header)
        f.flush()
        sys.stdout.write(header)
        sys.stdout.flush()

        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip("\n")
            out = f"[{_ts()}] {prefix} {line}\n"
            f.write(out)
            f.flush()
            sys.stdout.write(out)
            sys.stdout.flush()
        rc = proc.wait()
        footer = f"[{_ts()}] END {prefix} rc={rc}\n"
        f.write(footer)
        f.flush()
        sys.stdout.write(footer)
        sys.stdout.flush()
        return rc


@dataclass
class Step:
    name: str
    candidates: List[List[str]]
    log_name: str


def _default_steps() -> List[Step]:
    return [
        Step(
            name="artifact_gate",
            log_name="01_artifact_gate.log",
            candidates=[
                ["{py}", "scripts/artifact_gate.py"],
                ["{py}", "scripts/run_artifact_gate.py"],
                ["{py}", "tools/artifact_gate.py"],
                ["{mod}", "scripts.artifact_gate"],
                ["{mod}", "tools.artifact_gate"],
            ],
        ),
        Step(
            name="taxonomy_validation",
            log_name="02_taxonomy_validation.log",
            candidates=[
                ["{py}", "scripts/validate_taxonomy.py"],
                ["{py}", "scripts/taxonomy_validate.py"],
                ["{py}", "tools/validate_taxonomy.py"],
                ["{mod}", "scripts.validate_taxonomy"],
                ["{mod}", "tools.validate_taxonomy"],
            ],
        ),
        Step(
            name="toy_meta_analysis_demo",
            log_name="03_toy_meta_analysis_demo.log",
            candidates=[
                ["{py}", "scripts/toy_meta_analysis_demo.py"],
                ["{py}", "scripts/meta_analysis_demo.py"],
                ["{py}", "demos/toy_meta_analysis_demo.py"],
                ["{mod}", "scripts.toy_meta_analysis_demo"],
                ["{mod}", "demos.toy_meta_analysis_demo"],
            ],
        ),
    ]


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="One-command build runner (artifact gate -> taxonomy validation -> toy meta-analysis demo).")
    ap.add_argument("--build-dir", default="_build", help="Build output directory (relative to project root).")
    ap.add_argument("--clean", action="store_true", help="Delete build directory before running.")
    ap.add_argument("--quiet", action="store_true", help="Reduce console output (still writes logs).")
    args = ap.parse_args(argv)

    root = _project_root()
    build_dir = (root / args.build_dir).resolve()
    logs_dir = build_dir / "logs"
    _ensure_dir(build_dir)

    if args.clean and build_dir.exists():
        shutil.rmtree(build_dir, ignore_errors=True)
        _ensure_dir(build_dir)

    _ensure_dir(logs_dir)
    run_meta = {
        "started_at": _ts(),
        "project_root": str(root),
        "build_dir": str(build_dir),
        "steps": [],
        "status": "running",
    }
    summary_path = build_dir / "build_summary.json"
    _write_json(summary_path, run_meta)

    env = dict(os.environ)
    env["BUILD_DIR"] = str(build_dir)
    env["PYTHONUNBUFFERED"] = "1"

    steps = _default_steps()
    for step in steps:
        t0 = time.time()
        cmd = _select_command(root, step.candidates)
        if not cmd:
            run_meta["status"] = "error"
            run_meta["ended_at"] = _ts()
            run_meta["error"] = f"Could not find runnable command for step '{step.name}'. Tried: {step.candidates}"
            _write_json(summary_path, run_meta)
            sys.stderr.write(run_meta["error"] + "\n")
            return 2

        log_file = logs_dir / step.log_name
        prefix = f"{step.name}:"
        if args.quiet:
            with log_file.open("a", encoding="utf-8") as f:
                f.write(f"[{_ts()}] START {prefix} cmd={cmd} cwd={root}\n")
            rc = subprocess.call(cmd, cwd=str(root), env=env)
            with log_file.open("a", encoding="utf-8") as f:
                f.write(f"[{_ts()}] END {prefix} rc={rc}\n")
        else:
            rc = _tee_run(cmd, cwd=root, env=env, log_file=log_file, prefix=prefix)

        dur_s = round(time.time() - t0, 3)
        run_meta["steps"].append(
            {"name": step.name, "cmd": cmd, "log_file": str(log_file), "rc": rc, "duration_s": dur_s, "ended_at": _ts()}
        )
        _write_json(summary_path, run_meta)

        if rc != 0:
            run_meta["status"] = "failed"
            run_meta["ended_at"] = _ts()
            _write_json(summary_path, run_meta)
            sys.stderr.write(f"Build failed at step '{step.name}' (rc={rc}). See log: {_rel(root, log_file)}\n")
            return rc

    run_meta["status"] = "ok"
    run_meta["ended_at"] = _ts()
    _write_json(summary_path, run_meta)
    if not args.quiet:
        sys.stdout.write(f"[{_ts()}] BUILD OK. Summary: {_rel(root, summary_path)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
