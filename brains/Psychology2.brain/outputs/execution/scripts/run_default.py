from __future__ import annotations

import os
import sys
import shlex
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = REPO_ROOT / "runtime"
BUILD_DIR = RUNTIME_DIR / "_build"


def _run(cmd: list[str], *, cwd: Path | None = None) -> None:
    p = subprocess.run(cmd, cwd=str(cwd or REPO_ROOT), text=True)
    if p.returncode != 0:
        raise SystemExit(p.returncode)


def _candidate_default_build_cmd() -> list[list[str]]:
    py = sys.executable

    # Prefer explicit build entrypoints if they exist (most common first).
    candidates: list[tuple[Path, list[str]]] = [
        (REPO_ROOT / "scripts" / "build.py", [py, str(REPO_ROOT / "scripts" / "build.py")]),
        (REPO_ROOT / "scripts" / "run_build.py", [py, str(REPO_ROOT / "scripts" / "run_build.py")]),
        (REPO_ROOT / "scripts" / "pipeline.py", [py, str(REPO_ROOT / "scripts" / "pipeline.py")]),
        (REPO_ROOT / "build.py", [py, str(REPO_ROOT / "build.py")]),
        (REPO_ROOT / "main.py", [py, str(REPO_ROOT / "main.py")]),
    ]
    existing = [cmd for path, cmd in candidates if path.exists() and path.is_file()]
    if existing:
        return [existing[0]]

    # Fallback to `make build` if a Makefile exists.
    if (REPO_ROOT / "Makefile").exists():
        return [["make", "build"]]

    # Last resort: run any script that looks like the project's main runner.
    # (Avoid running run_default recursively.)
    scripts_dir = REPO_ROOT / "scripts"
    if scripts_dir.exists():
        for p in sorted(scripts_dir.glob("run_*.py")):
            if p.name == Path(__file__).name:
                continue
            return [[py, str(p)]]

    return []


def _verify() -> None:
    py = sys.executable
    verifier = REPO_ROOT / "verify_build_artifacts.py"
    if verifier.exists() and verifier.is_file():
        _run([py, str(verifier)])
        return

    verifier = REPO_ROOT / "scripts" / "verify_build_artifacts.py"
    if verifier.exists() and verifier.is_file():
        _run([py, str(verifier)])
        return

    raise SystemExit(
        "verify_build_artifacts.py not found at repo root or scripts/; cannot verify build artifacts."
    )


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # Allow overriding the build command via env var to make CI/local deterministic.
    # Example: DEFAULT_BUILD_CMD="python scripts/build.py --all"
    env_cmd = os.environ.get("DEFAULT_BUILD_CMD", "").strip()
    if env_cmd:
        build_cmds = [shlex.split(env_cmd)]
    else:
        build_cmds = _candidate_default_build_cmd()

    if not build_cmds:
        raise SystemExit(
            "No default build command found. Set DEFAULT_BUILD_CMD or add a standard build entrypoint."
        )

    # Ensure runtime directories exist so downstream steps can write artifacts.
    (RUNTIME_DIR).mkdir(parents=True, exist_ok=True)
    (BUILD_DIR).mkdir(parents=True, exist_ok=True)

    for cmd in build_cmds:
        _run(cmd)

    _verify()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
