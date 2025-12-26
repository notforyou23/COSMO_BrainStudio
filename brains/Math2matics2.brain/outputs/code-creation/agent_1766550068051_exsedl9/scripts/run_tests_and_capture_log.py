#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import platform
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


@dataclass
class RunMeta:
    started_at_utc: str
    finished_at_utc: str
    duration_seconds: float
    cwd: str
    command: List[str]
    exit_code: int
    python_executable: str
    python_version: str
    platform: str


def utc_ts_compact(dt: Optional[datetime] = None) -> str:
    dt = dt or datetime.now(timezone.utc)
    return dt.strftime('%Y%m%dT%H%M%SZ')


def default_test_command() -> List[str]:
    try:
        import importlib.util
        has_pytest = importlib.util.find_spec("pytest") is not None
    except Exception:
        has_pytest = False
    if has_pytest:
        return [sys.executable, "-m", "pytest", "-q"]
    return [sys.executable, "-m", "unittest", "discover", "-v"]


def parse_command_env(env_value: str) -> List[str]:
    env_value = (env_value or "").strip()
    if not env_value:
        return default_test_command()
    return shlex.split(env_value)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")


def run_and_capture(cmd: List[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        env=os.environ.copy(),
    )


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    outputs_dir = repo_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    started = datetime.now(timezone.utc)
    ts = utc_ts_compact(started)
    base = f"{ts}_tests"

    cmd = parse_command_env(os.environ.get("TEST_COMMAND", ""))

    proc: Optional[subprocess.CompletedProcess] = None
    exit_code = 1
    try:
        proc = run_and_capture(cmd, repo_root)
        exit_code = int(proc.returncode)
    except FileNotFoundError as e:
        proc = None
        exit_code = 127
        err = f"Failed to execute test command: {e}\nCommand: {cmd}\n"
        write_text(outputs_dir / f"{base}.stderr.log", err)
        write_text(outputs_dir / f"{base}.stdout.log", "")
    except Exception as e:
        proc = None
        exit_code = 1
        err = f"Unexpected error executing test command: {type(e).__name__}: {e}\nCommand: {cmd}\n"
        write_text(outputs_dir / f"{base}.stderr.log", err)
        write_text(outputs_dir / f"{base}.stdout.log", "")
    finally:
        finished = datetime.now(timezone.utc)

    if proc is not None:
        write_text(outputs_dir / f"{base}.stdout.log", proc.stdout or "")
        write_text(outputs_dir / f"{base}.stderr.log", proc.stderr or "")

    python_version = sys.version.replace("\n", " ").strip()
    py_info = "\n".join(
        [
            f"executable: {sys.executable}",
            f"version: {python_version}",
            f"platform: {platform.platform()}",
        ]
    )
    write_text(outputs_dir / f"{base}.python.txt", py_info)

    try:
        pf = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            cwd=str(repo_root),
            text=True,
            capture_output=True,
            env=os.environ.copy(),
        )
        pip_freeze_text = (pf.stdout or "") + (("\n# pip freeze stderr:\n" + (pf.stderr or "")) if (pf.stderr or "").strip() else "")
    except Exception as e:
        pip_freeze_text = f"# Failed to run pip freeze: {type(e).__name__}: {e}\n"
    write_text(outputs_dir / f"{base}.pip_freeze.txt", pip_freeze_text)

    meta = RunMeta(
        started_at_utc=started.isoformat(),
        finished_at_utc=finished.isoformat(),
        duration_seconds=(finished - started).total_seconds(),
        cwd=str(repo_root),
        command=cmd,
        exit_code=exit_code,
        python_executable=sys.executable,
        python_version=python_version,
        platform=platform.platform(),
    )
    (outputs_dir / f"{base}.meta.json").write_text(json.dumps(asdict(meta), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
