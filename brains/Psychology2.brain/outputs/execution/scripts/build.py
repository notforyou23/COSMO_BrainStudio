#!/usr/bin/env python3
"""One-command build entrypoint.

Runs the repository build runner with sensible defaults for local usage and CI.
All outputs/logs are directed to _build/ unless explicitly overridden.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _repo_root() -> Path:
    # scripts/build.py -> repo root
    return Path(__file__).resolve().parents[1]


def _add_repo_to_syspath(repo_root: Path) -> None:
    repo_str = str(repo_root)
    if repo_str not in sys.path:
        sys.path.insert(0, repo_str)


def _import_build_runner():
    # Supports both "src/" layout and direct module usage.
    tried = []
    for mod in ("src.build_runner", "build_runner"):
        try:
            __import__(mod)
            return sys.modules[mod]
        except Exception as e:  # noqa: BLE001
            tried.append((mod, repr(e)))
    msg = ["Failed to import build runner. Tried:"]
    msg += [f"  - {m}: {e}" for m, e in tried]
    raise ImportError("\n".join(msg))


def _call_runner(mod, *, project_root: Path, out_dir: Path, args: list[str]) -> int:
    # Prefer a CLI-style entrypoint if present.
    for name in ("cli", "main"):
        fn = getattr(mod, name, None)
        if callable(fn):
            try:
                res = fn(args)
                return int(res) if res is not None else 0
            except SystemExit as e:
                return int(e.code) if e.code is not None else 0

    # Otherwise try a programmatic API.
    for name in ("run", "run_build", "build"):
        fn = getattr(mod, name, None)
        if callable(fn):
            res = fn(project_root=project_root, out_dir=out_dir)
            return int(res) if res is not None else 0

    raise AttributeError(
        "build_runner module has no supported entrypoint (expected cli/main or run/run_build/build)."
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    rr = _repo_root()
    p = argparse.ArgumentParser(prog="build", description="Run the one-command build runner.")
    p.add_argument(
        "--project-root",
        type=Path,
        default=rr,
        help="Repository root (default: inferred from scripts/build.py).",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=rr / "_build",
        help="Build output directory (default: <project-root>/_build).",
    )
    p.add_argument(
        "--ci",
        action="store_true",
        help="CI mode (sets CI=1, useful for deterministic logging).",
    )
    p.add_argument(
        "--",
        dest="passthrough_sep",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    p.add_argument(
        "passthrough",
        nargs=argparse.REMAINDER,
        help="Arguments passed through to the underlying build runner (if it supports CLI args).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    ns = parse_args(list(sys.argv[1:] if argv is None else argv))
    project_root = ns.project_root.resolve()
    out_dir = (project_root / ns.out_dir).resolve() if not ns.out_dir.is_absolute() else ns.out_dir.resolve()

    os.environ.setdefault("PROJECT_ROOT", str(project_root))
    os.environ.setdefault("BUILD_DIR", str(out_dir))
    os.environ.setdefault("OUT_DIR", str(out_dir))
    if ns.ci:
        os.environ["CI"] = os.environ.get("CI", "1")

    _add_repo_to_syspath(project_root)

    try:
        mod = _import_build_runner()
    except Exception as e:  # noqa: BLE001
        print(str(e), file=sys.stderr)
        return 2

    runner_args = []
    runner_args += ["--project-root", str(project_root)]
    runner_args += ["--out-dir", str(out_dir)]
    runner_args += list(ns.passthrough)

    try:
        return _call_runner(mod, project_root=project_root, out_dir=out_dir, args=runner_args)
    except Exception as e:  # noqa: BLE001
        print(f"Build invocation failed: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
