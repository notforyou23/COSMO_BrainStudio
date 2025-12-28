#!/usr/bin/env python3
"""artifacts_validator.py

Validates presence of expected build artifacts and emits actionable preflight
diagnostics to _build/<run_id>/logs/ before any exit.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import glob
import json
import os
import platform
import subprocess
import sys
from pathlib import Path


EXIT_OK = 0
EXIT_USAGE = 2
EXIT_PREFLIGHT = 10
EXIT_MISSING = 20
EXIT_ERROR = 70


def _now_utc() -> str:
    return _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _resolve_run_id(cli_run_id: str | None) -> str:
    for k in ("RUN_ID", "BUILD_RUN_ID", "GITHUB_RUN_ID"):
        v = os.environ.get(k)
        if v:
            return str(v)
    if cli_run_id:
        return str(cli_run_id)
    return f"local_{_dt.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}_{os.getpid()}"


def _ensure_log_dir(run_id: str) -> Path:
    base = Path.cwd()
    log_dir = base / "_build" / run_id / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Best-effort fallback into cwd so we can at least log the failure.
        log_dir = base / "_build_logs_fallback"
        log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def _write_log(log_dir: Path, name: str, payload: object) -> None:
    p = log_dir / name
    try:
        p.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    except Exception:
        # Last-resort: stderr only.
        print(f"FAILED_TO_WRITE_LOG:{p}", file=sys.stderr)
        print(str(payload)[:2000], file=sys.stderr)


def _collect_mounts() -> list[str]:
    mounts: list[str] = []
    try:
        proc = Path("/proc/mounts")
        if proc.exists():
            mounts = proc.read_text(encoding="utf-8", errors="replace").splitlines()[:2000]
            return mounts
    except Exception:
        pass
    try:
        out = subprocess.check_output(["mount"], stderr=subprocess.STDOUT, text=True)
        mounts = out.splitlines()[:2000]
    except Exception:
        mounts = []
    return mounts


def _path_diag(p: Path) -> dict:
    d: dict = {"path": str(p)}
    try:
        d["exists"] = p.exists()
        d["is_file"] = p.is_file()
        d["is_dir"] = p.is_dir()
    except Exception as e:
        d["stat_error"] = repr(e)
        return d
    try:
        d["readable"] = os.access(p, os.R_OK)
        d["writable"] = os.access(p, os.W_OK)
        d["executable"] = os.access(p, os.X_OK)
    except Exception as e:
        d["access_error"] = repr(e)
    try:
        if d.get("exists"):
            st = p.stat()
            d["mode_octal"] = oct(st.st_mode & 0o7777)
            d["size"] = getattr(st, "st_size", None)
            d["mtime"] = _dt.datetime.utcfromtimestamp(st.st_mtime).isoformat() + "Z"
    except Exception as e:
        d["stat_detail_error"] = repr(e)
    return d


def preflight(
    run_id: str,
    expected_globs: list[str],
    base_dir: Path,
    extra_paths: list[Path],
) -> tuple[Path, dict]:
    log_dir = _ensure_log_dir(run_id)

    um = None
    try:
        old = os.umask(0)
        os.umask(old)
        um = oct(old)
    except Exception:
        um = None

    env_keys = [
        "PWD",
        "HOME",
        "USER",
        "CI",
        "RUN_ID",
        "BUILD_RUN_ID",
        "GITHUB_RUN_ID",
        "GITHUB_WORKSPACE",
        "WORKSPACE",
        "EXPECTED_ARTIFACTS",
    ]
    env_subset = {k: os.environ.get(k) for k in env_keys if k in os.environ}

    diags: dict = {
        "timestamp_utc": _now_utc(),
        "argv": sys.argv,
        "cwd": str(Path.cwd()),
        "base_dir": str(base_dir),
        "python": sys.version.replace("\n", " "),
        "executable": sys.executable,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
        },
        "ids": {
            "uid": getattr(os, "getuid", lambda: None)(),
            "gid": getattr(os, "getgid", lambda: None)(),
            "euid": getattr(os, "geteuid", lambda: None)(),
            "egid": getattr(os, "getegid", lambda: None)(),
            "umask": um,
        },
        "env": env_subset,
        "mounts_sample": _collect_mounts(),
        "paths": {},
        "expected_globs": expected_globs,
        "glob_results": {},
    }

    # Core paths to diagnose
    core_paths = [
        base_dir,
        Path.cwd(),
        log_dir,
        (Path.cwd() / "_build"),
        (Path.cwd() / "_build" / run_id),
    ]
    for p in core_paths + list(extra_paths):
        diags["paths"][str(p)] = _path_diag(p)

    # Glob expansion diagnostics (relative to base_dir)
    for pat in expected_globs:
        abs_pat = str((base_dir / pat).as_posix()) if not os.path.isabs(pat) else pat
        try:
            matches = sorted(glob.glob(abs_pat, recursive=True))
        except Exception as e:
            diags["glob_results"][pat] = {"abs_pattern": abs_pat, "error": repr(e), "matches": []}
            continue
        diags["glob_results"][pat] = {"abs_pattern": abs_pat, "count": len(matches), "matches": matches[:200]}

    _write_log(log_dir, "artifacts_validator_preflight.json", diags)
    return log_dir, diags


def _parse_expected(args: argparse.Namespace) -> list[str]:
    expected: list[str] = []
    if args.expected:
        expected.extend(args.expected)
    env = os.environ.get("EXPECTED_ARTIFACTS")
    if env:
        for part in env.split(","):
            part = part.strip()
            if part:
                expected.append(part)
    # De-dup while preserving order
    seen = set()
    out: list[str] = []
    for e in expected:
        if e not in seen:
            seen.add(e)
            out.append(e)
    return out


def validate(expected_globs: list[str], base_dir: Path) -> tuple[bool, dict]:
    missing: list[str] = []
    present: dict[str, int] = {}
    for pat in expected_globs:
        abs_pat = str((base_dir / pat).as_posix()) if not os.path.isabs(pat) else pat
        matches = sorted(glob.glob(abs_pat, recursive=True))
        present[pat] = len(matches)
        if len(matches) == 0:
            missing.append(pat)
    return (len(missing) == 0), {"missing_globs": missing, "present_counts": present}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Validate expected artifacts with preflight diagnostics.")
    ap.add_argument("--run-id", default=None, help="Run id for _build/<run_id>/logs/. Defaults from env or generated.")
    ap.add_argument("--base-dir", default=None, help="Base directory for relative glob patterns (default: cwd).")
    ap.add_argument(
        "--expected",
        action="append",
        default=[],
        help="Expected artifact glob (repeatable). Also supports env EXPECTED_ARTIFACTS=pat1,pat2",
    )
    ap.add_argument("--extra-path", action="append", default=[], help="Additional paths to diagnose (repeatable).")
    args = ap.parse_args(argv)

    run_id = _resolve_run_id(args.run_id)
    base_dir = Path(args.base_dir).resolve() if args.base_dir else Path.cwd().resolve()
    extra_paths = [Path(p).expanduser().resolve() for p in (args.extra_path or [])]

    expected_globs = _parse_expected(args)
    if not expected_globs:
        # Still write diagnostics so callers see environment and filesystem state.
        log_dir, _ = preflight(run_id, [], base_dir, extra_paths)
        _write_log(
            log_dir,
            "artifacts_validator_result.json",
            {
                "timestamp_utc": _now_utc(),
                "status": "error",
                "error": "No expected artifacts configured; pass --expected or set EXPECTED_ARTIFACTS.",
                "exit_code": EXIT_USAGE,
            },
        )
        print(f"ARTIFACTS_VALIDATOR_ERROR: no expected globs; logs at {log_dir}", file=sys.stderr)
        return EXIT_USAGE

    log_dir, _ = preflight(run_id, expected_globs, base_dir, extra_paths)

    try:
        ok, details = validate(expected_globs, base_dir)
        payload = {
            "timestamp_utc": _now_utc(),
            "status": "ok" if ok else "missing",
            "base_dir": str(base_dir),
            **details,
            "exit_code": EXIT_OK if ok else EXIT_MISSING,
        }
        _write_log(log_dir, "artifacts_validator_result.json", payload)
        if not ok:
            print(f"ARTIFACTS_VALIDATOR_MISSING: {details['missing_globs']}; logs at {log_dir}", file=sys.stderr)
            return EXIT_MISSING
        return EXIT_OK
    except SystemExit:
        raise
    except Exception as e:
        _write_log(
            log_dir,
            "artifacts_validator_result.json",
            {
                "timestamp_utc": _now_utc(),
                "status": "error",
                "error": repr(e),
                "exit_code": EXIT_ERROR,
            },
        )
        print(f"ARTIFACTS_VALIDATOR_ERROR: {e!r}; logs at {log_dir}", file=sys.stderr)
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
