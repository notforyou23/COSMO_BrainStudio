#!/usr/bin/env python3
"""QA CLI entrypoint.

Adds --diagnostic mode to invoke the Docker-based diagnostic workflow and route
outputs to outputs/qa/logs/ while preserving existing QA run behavior.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_DIR = REPO_ROOT / "outputs" / "qa" / "logs"


def _ensure_log_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def _import_and_run(module: str, argv: list[str]) -> int:
    mod = __import__(module, fromlist=["main"])
    main = getattr(mod, "main", None)
    if not callable(main):
        raise SystemExit(f"{module}.main not found")
    rc = main(argv)
    return int(rc) if rc is not None else 0


def _run_pytest_passthrough(argv: list[str], log_dir: Path) -> int:
    log_path = log_dir / "qa_run.log"
    cmd = [sys.executable, "-m", "pytest"] + argv
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("QA_LOG_DIR", str(log_dir))
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("CMD: " + " ".join(cmd) + "\n")
        f.flush()
        p = subprocess.Popen(
            cmd,
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
        assert p.stdout is not None
        for line in p.stdout:
            sys.stdout.write(line)
            f.write(line)
        return int(p.wait())


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    parser = argparse.ArgumentParser(prog="qa_run", add_help=True)
    parser.add_argument(
        "--diagnostic",
        action="store_true",
        help="Run Docker-based diagnostic workflow with maximal telemetry.",
    )
    parser.add_argument(
        "--log-dir",
        default=None,
        help="Override log directory (default: outputs/qa/logs).",
    )
    parser.add_argument(
        "--",
        dest="sep",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    ns, rest = parser.parse_known_args(argv)

    log_dir = _ensure_log_dir(Path(ns.log_dir) if ns.log_dir else DEFAULT_LOG_DIR)
    os.environ.setdefault("QA_LOG_DIR", str(log_dir))

    if ns.diagnostic:
        # Prefer the new diagnostic workflow if present.
        try:
            return _import_and_run("scripts.qa.diagnostic_run", ["--log-dir", str(log_dir)] + rest)
        except Exception as e:
            # Always leave a clue in logs for the failure to load/execute.
            (log_dir / "diagnostic_entrypoint_error.txt").write_text(
                f"Failed to run scripts.qa.diagnostic_run: {type(e).__name__}: {e}\n",
                encoding="utf-8",
            )
            raise

    # Preserve existing behavior by delegating if a legacy runner exists.
    for mod in ("scripts.qa.run", "scripts.qa.qa_run", "scripts.qa.standard_run"):
        try:
            return _import_and_run(mod, ["--log-dir", str(log_dir)] + rest)
        except ModuleNotFoundError:
            continue
        except SystemExit as e:
            return int(getattr(e, "code", 1) or 0)

    # Fallback: run pytest directly and capture output to outputs/qa/logs/qa_run.log.
    return _run_pytest_passthrough(rest, log_dir)


if __name__ == "__main__":
    raise SystemExit(main())
