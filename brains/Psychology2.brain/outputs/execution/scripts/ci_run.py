"""CI entrypoint: run the repo's one-command runner, then verify build outputs."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _split_cmd(cmd: str) -> list[str]:
    parts = shlex.split(cmd)
    if not parts:
        raise ValueError("Empty command string.")
    return parts


def _discover_default_cmd(root: Path) -> list[str]:
    candidates: list[list[str]] = [
        ["python", "-m", "scripts.one_command_runner"],
        ["python", "-m", "scripts.run"],
        ["python", "-m", "runtime.run"],
        ["python", "-m", "runtime.runner"],
        ["python", "scripts/one_command_runner.py"],
        ["python", "scripts/run.py"],
        ["python", "run.py"],
        ["bash", "scripts/run.sh"],
        ["bash", "run.sh"],
        ["make", "run"],
    ]
    for cmd in candidates:
        if cmd[:2] == ["python", "-m"]:
            mod = cmd[2]
            mod_path = root / Path(*mod.split(".")).with_suffix(".py")
            if mod_path.exists():
                return cmd
        elif cmd and cmd[0] in {"python", "bash"} and len(cmd) >= 2:
            if (root / cmd[1]).exists():
                return cmd
        else:
            return cmd
    raise SystemExit(
        "Could not discover a default one-command runner. "
        "Pass a command as args, or set CI_RUN_CMD."
    )


def run_one_command_runner(root: Path, argv: list[str]) -> int:
    env_cmd = os.getenv("CI_RUN_CMD", "").strip()
    if argv:
        cmd = argv
    elif env_cmd:
        cmd = _split_cmd(env_cmd)
    else:
        cmd = _discover_default_cmd(root)

    print("CI: running:", " ".join(shlex.quote(c) for c in cmd))
    proc = subprocess.run(cmd, cwd=str(root), check=False)
    return int(proc.returncode)


def _has_non_hidden_artifact(dir_path: Path) -> bool:
    if not dir_path.exists() or not dir_path.is_dir():
        return False
    for p in dir_path.rglob("*"):
        name = p.name
        if name.startswith(".") or name == ".gitkeep":
            continue
        if p.is_file():
            return True
    return False


def validate_build_outputs(root: Path) -> None:
    build_dir = root / "runtime" / "_build"
    reports = build_dir / "reports"
    tables = build_dir / "tables"

    errors: list[str] = []
    if not _has_non_hidden_artifact(reports):
        errors.append(f"Missing/empty reports: {reports}")
    if not _has_non_hidden_artifact(tables):
        errors.append(f"Missing/empty tables: {tables}")

    if errors:
        for e in errors:
            print("CI: ERROR:", e, file=sys.stderr)
        raise SystemExit(2)

    print("CI: build outputs OK")


def main(argv: list[str]) -> int:
    root = _repo_root()
    rc = run_one_command_runner(root, argv)
    if rc != 0:
        print(f"CI: runner failed with exit code {rc}", file=sys.stderr)
        return rc
    validate_build_outputs(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
