#!/usr/bin/env python3
"""Reproducible minimal failing-case generator for smoke-test instrumentation.

Modes:
  ok                -> writes artifacts and exits 0
  nonzero           -> writes artifacts and exits with nonzero code
  timeout           -> sleeps for a long time (simulated hang)
  missing_artifacts -> exits 0 but intentionally skips required artifacts
  crash             -> raises an exception (traceback to stderr)
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from pathlib import Path


def _env_snapshot() -> dict:
    keys = [
        "HOSTNAME",
        "USER",
        "HOME",
        "PWD",
        "PATH",
        "PYTHONPATH",
        "CI",
        "GITHUB_ACTIONS",
        "RUNNER_OS",
    ]
    env = {k: os.environ.get(k) for k in keys if os.environ.get(k) is not None}
    env["python_executable"] = sys.executable
    env["python_version"] = sys.version.replace("\n", " ")
    env["platform"] = platform.platform()
    env["cwd"] = os.getcwd()
    return env


def _best_effort_resource_stats() -> dict:
    out: dict = {}
    try:
        import resource  # type: ignore

        r = resource.getrusage(resource.RUSAGE_SELF)
        out.update(
            {
                "ru_utime_s": getattr(r, "ru_utime", None),
                "ru_stime_s": getattr(r, "ru_stime", None),
                "ru_maxrss_kb": getattr(r, "ru_maxrss", None),
            }
        )
    except Exception as e:
        out["resource_error"] = repr(e)
    return out


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, obj: dict) -> None:
    _write_text(path, json.dumps(obj, indent=2, sort_keys=True) + "\n")


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--mode", default=os.environ.get("MFC_MODE", "ok"))
    p.add_argument("--outdir", default=os.environ.get("MFC_OUTDIR", "artifacts"))
    p.add_argument("--sleep-seconds", type=float, default=float(os.environ.get("MFC_SLEEP_SECONDS", "3600")))
    p.add_argument("--create", default=os.environ.get("MFC_CREATE", "result.txt,run.json"))
    p.add_argument("--skip", default=os.environ.get("MFC_SKIP", ""))
    p.add_argument("--exit-code", type=int, default=int(os.environ.get("MFC_EXIT_CODE", "2")))
    p.add_argument("--message", default=os.environ.get("MFC_MESSAGE", "minimal failing case"))
    args = p.parse_args(argv)

    outdir = Path(args.outdir)
    create = [s.strip() for s in args.create.split(",") if s.strip()]
    skip = set(s.strip() for s in args.skip.split(",") if s.strip())

    sys.stdout.write(f"MFC mode={args.mode} outdir={outdir.as_posix()}\n")
    sys.stdout.write(f"MFC message={args.message}\n")
    sys.stderr.write("MFC stderr: instrumentation validation line\n")

    run_meta = {
        "mode": args.mode,
        "message": args.message,
        "ts_epoch": time.time(),
        "pid": os.getpid(),
        "env": _env_snapshot(),
        "resource": _best_effort_resource_stats(),
        "outdir": outdir.as_posix(),
        "create": create,
        "skip": sorted(skip),
    }

    if args.mode == "timeout":
        _write_json(outdir / "run.json", run_meta)
        sys.stdout.flush()
        sys.stderr.flush()
        time.sleep(max(0.0, args.sleep_seconds))
        return 0

    if args.mode == "crash":
        _write_json(outdir / "run.json", run_meta)
        raise RuntimeError("MFC crash mode: deterministic exception")

    missing = (args.mode == "missing_artifacts")
    for name in create:
        if name in skip:
            continue
        if missing and name not in ("run.json",):
            continue
        if name.endswith(".json"):
            _write_json(outdir / name, {"ok": True, "name": name, "meta": run_meta})
        else:
            _write_text(outdir / name, f"ok=true\nname={name}\nmode={args.mode}\n")

    if args.mode == "nonzero":
        return int(args.exit_code)

    return 0


if __name__ == "__main__":
    try:
        rc = main(sys.argv[1:])
    except SystemExit as e:
        raise
    except Exception as e:
        sys.stderr.write(f"Unhandled exception: {e!r}\n")
        raise
    raise SystemExit(rc)
