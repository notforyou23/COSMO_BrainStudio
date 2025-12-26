#!/usr/bin/env python3
"""Ultra-minimal Python smoke test (gating pre-check).

Runs a subprocess using the current Python interpreter to print sys.version and
attempt key imports. Persists combined stdout/stderr to:
  /outputs/qa/logs/<timestamp>_smoke_test.log
Exit code matches the smoke-test subprocess return code (0 on success).
"""

from __future__ import annotations

import os
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def _timestamp() -> str:
    # Compact UTC timestamp with milliseconds
    dt = datetime.now(timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%S") + f"-{int(dt.microsecond/1000):03d}Z"


def _parse_imports(s: str) -> list[str]:
    items = []
    for part in (s or "").replace(";", ",").split(","):
        name = part.strip()
        if name:
            items.append(name)
    return items


def main() -> int:
    base_dir = Path("/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution")
    logs_dir = base_dir / "outputs" / "qa" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"{_timestamp()}_smoke_test.log"

    default_imports = [
        "json",
        "pathlib",
        "subprocess",
        "typing",
        "re",
        "math",
    ]
    extra = _parse_imports(os.environ.get("SMOKE_TEST_IMPORTS", ""))
    imports = default_imports + [m for m in extra if m not in default_imports]

    code_lines = [
        "import sys",
        "print('=== SMOKE TEST START ===')",
        "print('sys.executable:', sys.executable)",
        "print('sys.version:', sys.version.replace('\n',' '))",
        "print('platform:', sys.platform)",
        f"mods = {imports!r}",
        "failed = []",
        "for m in mods:",
        "    try:",
        "        __import__(m)",
        "        print('IMPORT_OK:', m)",
        "    except Exception as e:",
        "        failed.append((m, repr(e)))",
        "        print('IMPORT_FAIL:', m, repr(e))",
        "print('FAILED_IMPORTS_COUNT:', len(failed))",
        "if failed:",
        "    raise SystemExit(2)",
        "print('=== SMOKE TEST PASS ===')",
    ]
    cmd = [sys.executable, "-c", "\n".join(code_lines)]

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        combined = proc.stdout if proc.stdout is not None else ""
    except Exception as e:
        combined = f'=== SMOKE TEST ERROR ===\n{repr(e)}\n'
        proc = None

    try:
        log_path.write_text(combined, encoding="utf-8")
    except Exception:
        try:
            fallback = str(log_path) + ".fallback.txt"
            Path(fallback).write_text(combined, encoding="utf-8")
        except Exception:
            pass

    # Minimal console output; the full details are in the log file.
    print(f"SMOKE_TEST_LOG:{log_path}")

    if proc is None:
        return 3
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
