#!/usr/bin/env python3
from __future__ import annotations
import json, os, platform, socket, subprocess, sys, time
from pathlib import Path
from datetime import datetime, timezone

def _utc_ts():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S-%fZ")

def resolve_base_out_dir():
    candidates = []
    for p in (os.environ.get("OUT_DIR"), os.environ.get("OUTPUT_DIR"), os.environ.get("CI_OUT_DIR")):
        if p:
            candidates.append(Path(p))
    candidates += [Path("/out"), Path("/outputs")]
    candidates += [Path.cwd() / "out", Path.cwd() / "outputs"]
    candidates += [Path("/tmp") / "out", Path("/tmp") / "outputs"]
    for base in candidates:
        try:
            base.mkdir(parents=True, exist_ok=True)
            probe = base / ".write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return base
        except Exception:
            continue
    return Path.cwd()

def make_bundle_dir(base: Path):
    bundle_name = f"smoke_test_{_utc_ts()}_{os.getpid()}"
    d = base / bundle_name
    d.mkdir(parents=True, exist_ok=True)
    return d

def run_minimal_command():
    cmd = ["/bin/sh", "-lc", "echo SMOKE_TEST_OK"]
    start = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        end = time.time()
        return {
            "cmd": cmd,
            "exit_code": int(p.returncode),
            "stdout": p.stdout or "",
            "stderr": p.stderr or "",
            "start_unix": start,
            "end_unix": end,
            "duration_s": end - start,
        }
    except Exception as e:
        end = time.time()
        return {
            "cmd": cmd,
            "exit_code": 127,
            "stdout": "",
            "stderr": f"{type(e).__name__}: {e}",
            "start_unix": start,
            "end_unix": end,
            "duration_s": end - start,
        }

def write_bundle(bundle: Path, result: dict):
    (bundle / "stdout.txt").write_text(result.get("stdout",""), encoding="utf-8")
    (bundle / "stderr.txt").write_text(result.get("stderr",""), encoding="utf-8")
    meta = {
        "timestamp_utc": _utc_ts(),
        "bundle_dir": str(bundle),
        "exit_code": result.get("exit_code"),
        "cmd": result.get("cmd"),
        "duration_s": result.get("duration_s"),
        "start_unix": result.get("start_unix"),
        "end_unix": result.get("end_unix"),
        "cwd": os.getcwd(),
        "python": sys.version,
        "platform": platform.platform(),
        "hostname": socket.gethostname(),
        "env": {k: os.environ.get(k) for k in ["CI","GITHUB_ACTIONS","GITHUB_RUN_ID","GITHUB_SHA","GITHUB_REF","OUT_DIR","OUTPUT_DIR","CI_OUT_DIR"] if k in os.environ},
    }
    (bundle / "metadata.json").write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")

def main():
    base = resolve_base_out_dir()
    bundle = make_bundle_dir(base)
    result = run_minimal_command()
    write_bundle(bundle, result)
    print(f"SMOKE_TEST_BUNDLE_DIR={bundle}")
    print(f"SMOKE_TEST_EXIT_CODE={result.get('exit_code')}")
    sys.exit(int(result.get("exit_code") or 0))

if __name__ == "__main__":
    main()
