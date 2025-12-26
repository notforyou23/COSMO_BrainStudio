"""Run pytest and capture its stdout/stderr to outputs/test_run_log.txt.

Intended usage:
  python scripts/run_tests_and_capture_log.py

Exit code matches pytest's exit code.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence
def project_root() -> Path:
    # scripts/ is expected to live at <root>/scripts/
    return Path(__file__).resolve().parents[1]
def run_pytest(pytest_args: Sequence[str] | None = None) -> int:
    root = project_root()
    outputs_dir = root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    log_path = outputs_dir / "test_run_log.txt"

    args = ["pytest"]
    if pytest_args:
        args.extend(list(pytest_args))

    env = os.environ.copy()
    proc = subprocess.run(
        args,
        cwd=str(root),
        env=env,
        text=True,
        capture_output=True,
    )

    log_lines = [
        f"cwd: {root}",
        f"command: {' '.join(args)}",
        f"exit_code: {proc.returncode}",
        "",
        "=== STDOUT ===",
        proc.stdout or "",
        "",
        "=== STDERR ===",
        proc.stderr or "",
        "",
    ]
    log_path.write_text("\n".join(log_lines), encoding="utf-8")

    # Keep console output minimal: where the log was written and exit code.
    print(f"pytest_exit_code={proc.returncode} log={log_path}")
    return int(proc.returncode)
def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    return run_pytest(argv)


if __name__ == "__main__":
    raise SystemExit(main())
