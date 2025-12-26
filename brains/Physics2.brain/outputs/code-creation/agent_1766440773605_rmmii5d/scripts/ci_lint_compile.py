#!/usr/bin/env python3
"""CI helper: lint/format checks + compilation/import sanity.

Designed for GitHub Actions: always writes logs under artifacts/ci_lint_compile
so the workflow can upload them on failure.
"""
from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Sequence, Tuple


EXCLUDE_DIRS = {".git", ".venv", "venv", "__pycache__", "build", "dist", ".mypy_cache", ".pytest_cache"}
ARTIFACT_DIR = Path("artifacts") / "ci_lint_compile"


def repo_root() -> Path:
    here = Path(__file__).resolve()
    return here.parent.parent


def iter_py_files(root: Path) -> Iterable[Path]:
    for p in root.rglob("*.py"):
        parts = set(p.parts)
        if any(d in parts for d in EXCLUDE_DIRS):
            continue
        yield p


def run_cmd(cmd: Sequence[str], cwd: Path, log_path: Path, env: dict | None = None) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as f:
        f.write("$ " + " ".join(cmd) + "\n\n")
        proc = subprocess.run(cmd, cwd=str(cwd), env=env, text=True, capture_output=True)
        if proc.stdout:
            f.write(proc.stdout)
        if proc.stderr:
            f.write("\n[stderr]\n" + proc.stderr)
        f.write(f"\n\n[exit_code] {proc.returncode}\n")
    return proc.returncode


def tool_exists(argv0: str) -> bool:
    from shutil import which
    return which(argv0) is not None


def ast_parse_check(files: Sequence[Path], log_path: Path) -> int:
    """Fast syntax check that yields readable file/line errors."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    for p in files:
        try:
            ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        except Exception as e:  # SyntaxError, UnicodeDecodeError, etc.
            failures.append(f"{p}: {e.__class__.__name__}: {e}")
    with log_path.open("w", encoding="utf-8") as f:
        f.write("AST parse check\n\n")
        if failures:
            f.write("\n".join(failures) + "\n")
        else:
            f.write("OK\n")
    return 1 if failures else 0


def compileall_check(root: Path, log_path: Path) -> int:
    # compileall is a good proxy for bytecode compilation across the repo.
    cmd = [sys.executable, "-m", "compileall", "-q", str(root)]
    return run_cmd(cmd, cwd=root, log_path=log_path)


def lint_and_format(root: Path, log_dir: Path) -> Tuple[int, list[Path]]:
    """Runs ruff/black if available; otherwise emits a note and succeeds."""
    codes: list[int] = []
    logs: list[Path] = []

    # Prefer ruff for lint + formatting check.
    if tool_exists("ruff"):
        p1 = log_dir / "ruff_check.log"
        codes.append(run_cmd(["ruff", "check", "."], cwd=root, log_path=p1))
        logs.append(p1)
        p2 = log_dir / "ruff_format_check.log"
        codes.append(run_cmd(["ruff", "format", "--check", "."], cwd=root, log_path=p2))
        logs.append(p2)
    else:
        p = log_dir / "lint_missing_tools.log"
        p.write_text("ruff not found on PATH; skipping lint/format checks.\n", encoding="utf-8")
        logs.append(p)

    # Optional black check (some repos still use it); doesn't fail if missing.
    if tool_exists("black"):
        p = log_dir / "black_check.log"
        codes.append(run_cmd(["black", "--check", "."], cwd=root, log_path=p))
        logs.append(p)

    return (0 if all(c == 0 for c in codes) else 1), logs


def main(argv: Sequence[str]) -> int:
    root = repo_root()
    os.chdir(root)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(iter_py_files(root))
    if not files:
        (ARTIFACT_DIR / "note.log").write_text("No Python files found.\n", encoding="utf-8")
        return 0

    exit_code = 0

    lint_rc, _ = lint_and_format(root, ARTIFACT_DIR)
    exit_code |= lint_rc

    exit_code |= ast_parse_check(files, ARTIFACT_DIR / "ast_parse.log")
    exit_code |= compileall_check(root, ARTIFACT_DIR / "compileall.log")

    # A lightweight import smoke test for the package root if present.
    # Import errors often indicate missing deps; we still record them as CI failures.
    pkg = next((p for p in root.iterdir() if p.is_dir() and (p / "__init__.py").is_file()), None)
    if pkg is not None:
        exit_code |= run_cmd(
            [sys.executable, "-c", f"import importlib; importlib.import_module('{pkg.name}')"],
            cwd=root,
            log_path=ARTIFACT_DIR / "import_root_pkg.log",
            env=dict(os.environ, PYTHONPATH=str(root)),
        )

    print(f"ci_lint_compile: logs at {ARTIFACT_DIR}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
