import os
import subprocess
import sys


def _run(cmd, timeout=30):
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )


def test_cli_help_via_module():
    # Regression test: importing/running the CLI used to fail with a SyntaxError.
    proc = _run([sys.executable, "-m", "qg_bench.cli", "--help"])
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    out = (proc.stdout + proc.stderr).lower()
    assert "usage" in out or "help" in out or "options" in out


def test_cli_version_or_help_exits_successfully():
    # Some CLIs implement --version; if not, it should fail gracefully.
    proc = _run([sys.executable, "-m", "qg_bench.cli", "--version"])
    if proc.returncode != 0:
        proc = _run([sys.executable, "-m", "qg_bench.cli", "-h"])
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
