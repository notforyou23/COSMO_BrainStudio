#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _run_python_version() -> str:
    try:
        p = subprocess.run([sys.executable, "--version"], capture_output=True, text=True)
        out = (p.stdout or "").strip()
        err = (p.stderr or "").strip()
        return out or err or "UNKNOWN"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


def _try_import(name: str) -> str:
    try:
        __import__(name)
        return "OK"
    except Exception as e:
        return f"FAIL: {type(e).__name__}: {e}"


def _write_log(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Minimal smoke-test: python version + basic imports, writes a timestamped log.")
    ap.add_argument("--update-baseline", action="store_true", help="Copy the generated log to outputs/qa/logs/baseline_smoke_test.log")
    args = ap.parse_args(argv)

    root = Path(__file__).resolve().parents[2]
    logs_dir = root / "outputs" / "qa" / "logs"
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = logs_dir / f"{ts}_smoke_test.log"
    baseline_path = logs_dir / "baseline_smoke_test.log"

    lines = []
    lines.append(f"timestamp_utc={ts}")
    lines.append(f"python_dash_version={_run_python_version()}")
    lines.append(f"sys_version={sys.version.replace(os.linesep, ' ')}")
    lines.append(f"executable={sys.executable}")
    lines.append(f"platform={platform.platform()}")
    lines.append(f"cwd={os.getcwd()}")

    imports = ["json", "pathlib", "re", "math", "hashlib", "sqlite3", "ssl", "subprocess"]
    lines.append("imports:")
    for name in imports:
        lines.append(f"  {name}={_try_import(name)}")

    optional = ["numpy", "pandas", "requests", "yaml"]
    lines.append("optional_imports:")
    for name in optional:
        lines.append(f"  {name}={_try_import(name)}")

    text = "\n".join(lines) + "\n"
    _write_log(text, log_path)

    update = args.update_baseline or (os.environ.get("UPDATE_BASELINE", "").strip() in ("1", "true", "TRUE", "yes", "YES"))
    if update:
        _write_log(text, baseline_path)

    print(str(log_path))
    if update:
        print(f"BASELINE_UPDATED:{baseline_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
