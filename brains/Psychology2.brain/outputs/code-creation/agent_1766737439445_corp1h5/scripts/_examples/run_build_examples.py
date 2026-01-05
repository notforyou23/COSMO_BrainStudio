#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD_ROOT = ROOT / "_build" / "examples"


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _write(p: Path, text: str) -> None:
    _ensure_dir(p.parent)
    p.write_text(text, encoding="utf-8")


def _touch_empty(p: Path) -> None:
    _ensure_dir(p.parent)
    p.write_bytes(b"")


def _validate_artifact(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing required artifact: {path}")
    if path.is_dir():
        raise IsADirectoryError(f"Artifact must be a file, got directory: {path}")
    if path.stat().st_size == 0:
        raise ValueError(f"Empty required artifact: {path}")


def _run_step(name: str, build_dir: Path, fn) -> None:
    log_path = build_dir / "logs" / f"{name}.log"
    _ensure_dir(log_path.parent)
    with log_path.open("w", encoding="utf-8") as f:
        def log(msg: str) -> None:
            f.write(msg.rstrip("\n") + "\n")
            f.flush()
            print(msg, flush=True)

        log(f"[{name}] start")
        fn(log)
        log(f"[{name}] ok")


def _toy_build(build_dir: Path, required_artifact: Path) -> int:
    try:
        _ensure_dir(build_dir)
        _run_step("01_artifact_gate", build_dir, lambda log: (log(f"checking: {required_artifact}"), _validate_artifact(required_artifact)))
        _run_step("02_taxonomy_validation", build_dir, lambda log: (_write(build_dir / "out" / "taxonomy_validation.txt", "taxonomy ok\n"), log("wrote taxonomy_validation.txt")))
        _run_step("03_toy_meta_analysis_demo", build_dir, lambda log: (_write(build_dir / "out" / "toy_meta_analysis.txt", "meta-analysis demo ok\n"), log("wrote toy_meta_analysis.txt")))
        return 0
    except Exception as e:
        err = build_dir / "logs" / "build.error.log"
        _ensure_dir(err.parent)
        err.write_text(str(e).rstrip() + "\n", encoding="utf-8")
        print(f"[build] FAILED: {e}", file=sys.stderr, flush=True)
        print(f"[build] error log: {err}", file=sys.stderr, flush=True)
        return 2


def _run_as_subprocess(mode: str) -> int:
    cmd = [sys.executable, str(Path(__file__).resolve()), "--mode", mode]
    p = subprocess.run(cmd, cwd=str(ROOT))
    return p.returncode


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Runnable build examples: success + failing (missing/empty artifact).")
    ap.add_argument("--mode", choices=["success", "missing", "empty", "all"], default="all")
    args = ap.parse_args(argv)

    if args.mode == "all":
        BUILD_ROOT.mkdir(parents=True, exist_ok=True)
        print(f"examples build root: {BUILD_ROOT}")
        rc1 = _run_as_subprocess("success")
        rc2 = _run_as_subprocess("missing")
        rc3 = _run_as_subprocess("empty")
        print("exit_codes:", {"success": rc1, "missing": rc2, "empty": rc3})
        print(f"inspect outputs/logs under: {BUILD_ROOT}")
        return 0

    ex_dir = BUILD_ROOT / args.mode
    required = ex_dir / "inputs" / "required_artifact.txt"

    if args.mode == "success":
        _write(required, "non-empty artifact\n")
    elif args.mode == "missing":
        if required.exists():
            required.unlink()
    elif args.mode == "empty":
        _touch_empty(required)

    os.environ["BUILD_DIR"] = str(ex_dir)
    print(f"mode: {args.mode}")
    print(f"build dir: {ex_dir}")
    print(f"required artifact: {required}")
    rc = _toy_build(ex_dir, required)
    print(f"exit code: {rc}")
    print(f"logs: {(ex_dir / 'logs').resolve()}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
