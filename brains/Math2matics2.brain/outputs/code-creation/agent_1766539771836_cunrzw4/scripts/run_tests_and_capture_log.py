"""Run pytest and capture full console output to outputs/test.log.

Intended for CI/CD artifact retention. The exit code matches pytest's result.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
def _repo_root() -> Path:
    # scripts/ is expected to live directly under the repository root
    return Path(__file__).resolve().parents[1]
def run_pytest_and_capture_log(extra_args: list[str] | None = None) -> int:
    root = _repo_root()
    outputs_dir = root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)
    log_path = outputs_dir / "test.log"

    args = [sys.executable, "-m", "pytest"]
    if extra_args:
        args.extend(extra_args)

    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")

    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"COMMAND: {' '.join(args)}\n")
        log.write(f"CWD: {root}\n\n")
        log.flush()

        proc = subprocess.Popen(
            args,
            cwd=str(root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        assert proc.stdout is not None
        for line in proc.stdout:
            # Tee to console and file to retain full context in CI artifacts
            sys.stdout.write(line)
            log.write(line)

        return proc.wait()
def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    return run_pytest_and_capture_log(argv)


if __name__ == "__main__":
    raise SystemExit(main())
