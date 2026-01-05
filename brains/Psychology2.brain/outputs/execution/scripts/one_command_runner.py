"""one_command_runner.py

Runs the project's build command and then verifies build artifacts.

Goals:
- Always run artifact verification after build attempts so manifest is emitted.
- Fail the overall run if build fails or required artifacts are missing/empty.
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], cwd: Path) -> int:
    print("+ " + " ".join(shlex.quote(c) for c in cmd), flush=True)
    try:
        return subprocess.run(cmd, cwd=str(cwd), check=False).returncode
    except FileNotFoundError:
        return 127


def _default_build_cmd(repo_root: Path) -> list[str] | None:
    candidates = [
        repo_root / "scripts" / "build.py",
        repo_root / "scripts" / "run_build.py",
        repo_root / "build.py",
    ]
    for c in candidates:
        if c.is_file():
            return [sys.executable, str(c)]
    # If a build command was not found, return None; caller may provide --build-cmd.
    return None


def _verify_cmd(repo_root: Path) -> list[str] | None:
    verifier = repo_root / "scripts" / "verify_artifacts.py"
    if verifier.is_file():
        return [sys.executable, str(verifier)]
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="One-command build runner with artifact verification.")
    ap.add_argument("--repo-root", default=None, help="Repository root (defaults to parent of scripts/).")
    ap.add_argument(
        "--build-cmd",
        default=os.environ.get("ONE_COMMAND_BUILD_CMD"),
        help="Explicit build command to run (string, shell-like). Overrides autodetection.",
    )
    ap.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip build and only run artifact verification.",
    )
    ap.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip artifact verification (not recommended).",
    )
    args, extra = ap.parse_known_args(argv)

    if args.repo_root:
        repo_root = Path(args.repo_root).expanduser().resolve()
    else:
        repo_root = Path(__file__).resolve().parents[1]

    build_rc = 0
    verify_rc = 0

    try:
        if not args.skip_build:
            if args.build_cmd:
                build_cmd = shlex.split(args.build_cmd) + extra
            else:
                build_cmd = _default_build_cmd(repo_root)
                if build_cmd is None:
                    print("ERROR: No build command found. Provide --build-cmd or add scripts/build.py.", file=sys.stderr)
                    build_rc = 2
                else:
                    build_cmd = build_cmd + extra
            if build_rc == 0:
                build_rc = _run(build_cmd, cwd=repo_root)

    finally:
        if not args.skip_verify:
            vcmd = _verify_cmd(repo_root)
            if vcmd is None:
                print("ERROR: scripts/verify_artifacts.py not found; cannot verify artifacts.", file=sys.stderr)
                verify_rc = 2
            else:
                verify_rc = _run(vcmd, cwd=repo_root)

    if verify_rc != 0:
        return verify_rc
    return build_rc


if __name__ == "__main__":
    raise SystemExit(main())
