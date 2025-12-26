#!/usr/bin/env python3
"""Run pytest and capture a canonical set of run artifacts.

Artifacts (written under ./outputs):
- pytest_output.txt: full combined stdout/stderr from pytest
- run_metadata.json: structured execution metadata for the run
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_run(cmd: list[str], cwd: str | None = None) -> str | None:
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    except Exception:
        return None
    out = (p.stdout or "").strip()
    return out if p.returncode == 0 and out else None


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
def run_pytest(pytest_args: list[str], outputs_dir: Path, show_output: bool) -> dict:
    _ensure_parent(outputs_dir / "placeholder")
    output_path = outputs_dir / "pytest_output.txt"
    start_ts = _utc_now_iso()
    t0 = time.time()

    cmd = [sys.executable, "-m", "pytest"] + pytest_args
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")

    _ensure_parent(output_path)
    with output_path.open("w", encoding="utf-8", errors="replace") as f:
        f.write(f"# command: {' '.join(cmd)}\n")
        f.write(f"# started_utc: {start_ts}\n\n")
        f.flush()

        proc = subprocess.Popen(
            cmd,
            cwd=str(Path.cwd()),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            f.write(line)
            if show_output:
                print(line, end="")
        proc.wait()

    end_ts = _utc_now_iso()
    duration_s = round(time.time() - t0, 6)

    return {
        "command": cmd,
        "cwd": str(Path.cwd()),
        "returncode": proc.returncode,
        "started_utc": start_ts,
        "ended_utc": end_ts,
        "duration_seconds": duration_s,
        "artifacts": {
            "pytest_output_txt": str(output_path.as_posix()),
            "pytest_output_bytes": output_path.stat().st_size if output_path.exists() else None,
        },
    }
def build_metadata(base: dict, outputs_dir: Path) -> dict:
    repo_root = _safe_run(["git", "rev-parse", "--show-toplevel"])
    git_sha = _safe_run(["git", "rev-parse", "HEAD"])
    git_dirty = None
    if git_sha is not None:
        status = _safe_run(["git", "status", "--porcelain"])
        git_dirty = bool(status)

    pytest_version = _safe_run([sys.executable, "-m", "pytest", "--version"])
    base["environment"] = {
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "platform": platform.platform(),
        "pytest_version": pytest_version,
    }
    base["git"] = {"root": repo_root, "sha": git_sha, "dirty": git_dirty}
    base["artifacts"]["run_metadata_json"] = str((outputs_dir / "run_metadata.json").as_posix())
    return base
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Run pytest and write outputs/pytest_output.txt and outputs/run_metadata.json")
    p.add_argument("--outputs-dir", default="outputs", help="Directory to write run artifacts (default: outputs)")
    p.add_argument("--show-output", action="store_true", help="Also stream pytest output to this console")
    p.add_argument("pytest_args", nargs=argparse.REMAINDER, help="Arguments passed through to pytest (prefix with --)")
    args = p.parse_args(argv)

    pytest_args = list(args.pytest_args)
    if pytest_args and pytest_args[0] == "--":
        pytest_args = pytest_args[1:]

    outputs_dir = Path(args.outputs_dir)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    meta = run_pytest(pytest_args=pytest_args, outputs_dir=outputs_dir, show_output=args.show_output)
    meta = build_metadata(meta, outputs_dir=outputs_dir)

    meta_path = outputs_dir / "run_metadata.json"
    _ensure_parent(meta_path)
    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return int(meta.get("returncode", 1) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
