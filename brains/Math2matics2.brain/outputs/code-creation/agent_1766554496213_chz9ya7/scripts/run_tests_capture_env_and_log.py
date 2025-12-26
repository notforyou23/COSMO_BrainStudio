from __future__ import annotations

import datetime as _dt
import platform as _platform
import subprocess as _subprocess
import sys as _sys
from pathlib import Path as _Path


def _run(cmd: list[str], cwd: _Path) -> _subprocess.CompletedProcess:
    return _subprocess.run(
        cmd,
        cwd=str(cwd),
        text=True,
        capture_output=True,
    )


def main() -> int:
    repo_root = _Path(__file__).resolve().parents[1]
    outputs_dir = repo_root / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    date_str = _dt.date.today().isoformat()
    log_path = outputs_dir / f"test_run_log_{date_str}.txt"
    env_path = outputs_dir / f"env_{date_str}.txt"

    test_script = repo_root / "scripts" / "run_tests_and_capture_log.py"
    if not test_script.is_file():
        raise FileNotFoundError(f"Missing test runner: {test_script}")

    # Capture environment
    py_version = _sys.version.replace("\n", " ")
    py_exe = _sys.executable
    plat = _platform.platform()

    pip_freeze = _run([_sys.executable, "-m", "pip", "freeze"], cwd=repo_root)
    pip_freeze_text = (pip_freeze.stdout or "") + (pip_freeze.stderr or "")

    env_lines = [
        f"date: {date_str}",
        f"python_executable: {py_exe}",
        f"python_version: {py_version}",
        f"platform: {plat}",
        "",
        "pip_freeze:",
        pip_freeze_text.rstrip(),
        "",
        f"pip_freeze_exit_code: {pip_freeze.returncode}",
        "",
    ]
    env_path.write_text("\n".join(env_lines), encoding="utf-8")

    # Run tests and capture stdout/stderr + exit code
    proc = _run([_sys.executable, str(test_script)], cwd=repo_root)
    out = proc.stdout or ""
    err = proc.stderr or ""

    log_lines = [
        f"date: {date_str}",
        f"command: {_sys.executable} {test_script}",
        f"cwd: {repo_root}",
        "",
        "=== STDOUT ===",
        out.rstrip(),
        "",
        "=== STDERR ===",
        err.rstrip(),
        "",
        f"exit_code: {proc.returncode}",
        "",
    ]
    log_path.write_text("\n".join(log_lines), encoding="utf-8")

    # Print paths for linking in roadmap DoD
    print(f"TEST_LOG_PATH:{log_path.relative_to(repo_root)}")
    print(f"ENV_PATH:{env_path.relative_to(repo_root)}")

    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
