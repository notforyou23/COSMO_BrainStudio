#!/usr/bin/env python3
"""preflight_smoke.py

Lightweight preflight diagnostics intended to fail fast with actionable errors
when the execution environment is unstable (e.g., container lost before tests).

Prints:
- Python version + executable
- OS/platform info
- cwd + detected repo root (best-effort)
- disk space for repo root filesystem
- write permission checks (cwd + tempdir)

Exit codes:
- 0: OK
- 2: preflight failed (see error list)
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
import tempfile
from pathlib import Path


def _find_repo_root(start: Path) -> Path | None:
    """Walk up from start to find a likely repo root."""
    markers = (".git", "pyproject.toml", "setup.cfg", "setup.py", "requirements.txt")
    cur = start.resolve()
    for _ in range(50):
        for m in markers:
            if (cur / m).exists():
                return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def _format_bytes(n: int) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    x = float(n)
    for u in units:
        if x < 1024.0 or u == units[-1]:
            return f"{x:.1f} {u}" if u != "B" else f"{int(x)} B"
        x /= 1024.0
    return f"{n} B"


def _check_writable(dir_path: Path) -> tuple[bool, str]:
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return False, f"cannot create directory: {e}"
    probe = dir_path / f".preflight_write_probe_{os.getpid()}"
    try:
        probe.write_text("ok\n", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True, "ok"
    except Exception as e:
        try:
            probe.unlink(missing_ok=True)
        except Exception:
            pass
        return False, f"cannot write/delete files: {e}"


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    cwd = Path.cwd()
    repo_root = _find_repo_root(cwd) or _find_repo_root(Path(__file__).resolve())
    if repo_root is None:
        warnings.append("Repo root not detected (no .git/pyproject.toml/setup.cfg/setup.py/requirements.txt found while walking up).")

    print("=== PRE-FLIGHT SMOKE TEST ===")
    print(f"python: {sys.version.replace(os.linesep, ' ')}")
    print(f"executable: {sys.executable}")
    print(f"platform: {platform.platform()}  machine={platform.machine()}  processor={platform.processor() or 'unknown'}")
    print(f"cwd: {cwd}")
    print(f"script: {Path(__file__).resolve()}")
    print(f"repo_root: {repo_root if repo_root else 'UNKNOWN'}")

    check_base = repo_root or cwd
    try:
        usage = shutil.disk_usage(str(check_base))
        free = usage.free
        total = usage.total
        used = usage.used
        print(f"disk: base={check_base}  free={_format_bytes(free)}  used={_format_bytes(used)}  total={_format_bytes(total)}")
        min_free = int(os.environ.get("PREFLIGHT_MIN_DISK_BYTES", str(200 * 1024 * 1024)))  # default 200 MiB
        if free < min_free:
            errors.append(
                f"Low disk space on filesystem containing {check_base}: free={_format_bytes(free)} < required={_format_bytes(min_free)}. "
                "Free space (delete caches/artifacts) or increase disk allocation."
            )
    except Exception as e:
        errors.append(f"Failed to read disk usage for {check_base}: {e}")

    ok, msg = _check_writable(cwd)
    print(f"write_check_cwd: {'OK' if ok else 'FAIL'} ({msg})")
    if not ok:
        errors.append(
            f"Working directory not writable: {cwd} ({msg}). "
            "Ensure the runner mounts the workspace read-write and has permissions."
        )

    tmpdir = Path(tempfile.gettempdir())
    ok, msg = _check_writable(tmpdir)
    print(f"write_check_tmp: {'OK' if ok else 'FAIL'} ({tmpdir}; {msg})")
    if not ok:
        errors.append(
            f"Temp directory not writable: {tmpdir} ({msg}). "
            "Set TMPDIR to a writable path or fix filesystem permissions."
        )

    # Basic sanity checks that often correlate with abrupt termination.
    try:
        import resource  # type: ignore

        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        print(f"rlimit_nofile: soft={soft} hard={hard}")
        if soft != resource.RLIM_INFINITY and soft < 256:
            warnings.append(f"Low RLIMIT_NOFILE soft limit ({soft}); tests may fail with 'too many open files'.")
    except Exception:
        pass

    if warnings:
        print("--- WARNINGS ---")
        for w in warnings:
            print(f"WARN: {w}")

    if errors:
        print("--- ERRORS (action required) ---")
        for e in errors:
            print(f"ERROR: {e}")
        print("Preflight failed: refusing to run tests in an unstable environment.")
        return 2

    print("Preflight OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
