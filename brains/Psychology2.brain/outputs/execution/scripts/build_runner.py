#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _build_root(repo: Path) -> Path:
    return repo / "runtime" / "_build"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _write_text(p: Path, text: str) -> None:
    _ensure_dir(p.parent)
    p.write_text(text, encoding="utf-8")


def _run(cmd: list[str], cwd: Path, env: dict[str, str], log_fp, verbose: bool) -> dict:
    t0 = time.time()
    if verbose:
        print("+", " ".join(cmd), flush=True)
    p = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    out, err = p.communicate()
    dt = time.time() - t0
    log_fp.write(f"\n$ {' '.join(cmd)}\n")
    if out:
        log_fp.write(out)
        if not out.endswith("\n"):
            log_fp.write("\n")
    if err:
        log_fp.write(err)
        if not err.endswith("\n"):
            log_fp.write("\n")
    log_fp.write(f"[exit={p.returncode} elapsed={dt:.3f}s]\n")
    return {
        "cmd": cmd,
        "returncode": p.returncode,
        "elapsed_s": round(dt, 6),
        "stdout_len": len(out or ""),
        "stderr_len": len(err or ""),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Canonical build runner (writes to runtime/_build/).")
    ap.add_argument("--clean", action="store_true", help="Remove runtime/_build/ before running.")
    ap.add_argument("--skip-build", action="store_true", help="Only record environment info; do not build.")
    ap.add_argument("--verbose", action="store_true", help="Echo commands to stdout.")
    args = ap.parse_args(argv)

    repo = _repo_root()
    build_root = _build_root(repo)
    dist_dir = build_root / "dist"
    logs_dir = build_root / "logs"
    raw_dir = build_root / "raw"
    report_path = build_root / "build_report.json"
    log_path = logs_dir / "build.log"

    if args.clean and build_root.exists():
        shutil.rmtree(build_root)

    _ensure_dir(dist_dir)
    _ensure_dir(logs_dir)
    _ensure_dir(raw_dir)

    env = dict(os.environ)
    env["CANONICAL_BUILD_ROOT"] = str(build_root)
    env["CANONICAL_DIST_DIR"] = str(dist_dir)
    env["PYTHONUNBUFFERED"] = "1"

    meta = {
        "started_at": _now(),
        "repo_root": str(repo),
        "build_root": str(build_root),
        "dist_dir": str(dist_dir),
        "logs_dir": str(logs_dir),
        "raw_dir": str(raw_dir),
        "commands": [],
        "artifacts": [],
    }

    with open(log_path, "a", encoding="utf-8") as log_fp:
        log_fp.write(f"\n=== build_runner started {meta['started_at']} ===\n")
        meta["commands"].append(_run([sys.executable, "-V"], cwd=repo, env=env, log_fp=log_fp, verbose=args.verbose))
        meta["commands"].append(_run([sys.executable, "-m", "pip", "--version"], cwd=repo, env=env, log_fp=log_fp, verbose=args.verbose))

        if not args.skip_build:
            if (repo / "pyproject.toml").is_file():
                meta["commands"].append(_run([sys.executable, "-m", "build", "--outdir", str(dist_dir)], cwd=repo, env=env, log_fp=log_fp, verbose=args.verbose))
            elif (repo / "setup.py").is_file():
                meta["commands"].append(_run([sys.executable, "setup.py", "sdist", "bdist_wheel", "-d", str(dist_dir)], cwd=repo, env=env, log_fp=log_fp, verbose=args.verbose))
            else:
                log_fp.write("No pyproject.toml or setup.py found; skipping build step.\n")
                meta["commands"].append({"cmd": ["<no build config>"], "returncode": 0, "elapsed_s": 0.0, "stdout_len": 0, "stderr_len": 0})

        if dist_dir.exists():
            for p in sorted(dist_dir.glob("*")):
                if p.is_file():
                    meta["artifacts"].append({"path": str(p), "name": p.name, "size": p.stat().st_size})

        meta["finished_at"] = _now()
        meta["ok"] = all(c.get("returncode", 1) == 0 for c in meta["commands"])
        log_fp.write(f"=== build_runner finished {meta['finished_at']} ok={meta['ok']} ===\n")

    _write_text(report_path, json.dumps(meta, indent=2, sort_keys=True) + "\n")

    if not meta["ok"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
