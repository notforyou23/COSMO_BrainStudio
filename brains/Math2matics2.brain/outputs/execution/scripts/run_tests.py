from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    start = start.resolve()
    for p in [start, *start.parents]:
        if (p / "pyproject.toml").is_file() or (p / "setup.cfg").is_file() or (p / "setup.py").is_file():
            return p
    return start


def _stream_process(cmd: list[str], cwd: Path, log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "=== test run ===",
        f"timestamp_utc={datetime.utcnow().isoformat(timespec='seconds')}Z",
        f"python={sys.version.replace(os.linesep, ' ')}",
        f"executable={sys.executable}",
        f"platform={platform.platform()}",
        f"cwd={cwd}",
        f"cmd={' '.join(cmd)}",
        "",
    ]
    with log_path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(header))
        f.flush()

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )
        except FileNotFoundError as e:
            msg = f"ERROR: failed to start process: {e}\n"
            sys.stdout.write(msg)
            f.write(msg)
            return 127

        assert proc.stdout is not None
        for line in proc.stdout:
            sys.stdout.write(line)
            f.write(line)
        proc.wait()
        f.write(f"\n=== exit_code={proc.returncode} ===\n")
        return int(proc.returncode or 0)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run pytest and write a full transcript to outputs/test_run.log")
    ap.add_argument("--repo", default=None, help="Repository root (auto-detected if omitted)")
    ap.add_argument("--log", default=None, help="Log file path (default: <repo>/outputs/test_run.log)")
    ap.add_argument("pytest_args", nargs=argparse.REMAINDER, help="Arguments forwarded to pytest after '--'")
    ns = ap.parse_args(argv)

    here = Path(__file__).resolve()
    repo = Path(ns.repo).resolve() if ns.repo else _find_repo_root(here.parent)
    log_path = Path(ns.log).resolve() if ns.log else (repo / "outputs" / "test_run.log")

    pytest_args = list(ns.pytest_args or [])
    if pytest_args and pytest_args[0] == "--":
        pytest_args = pytest_args[1:]

    cmd = [sys.executable, "-m", "pytest", *pytest_args]
    return _stream_process(cmd, cwd=repo, log_path=log_path)


if __name__ == "__main__":
    raise SystemExit(main())
