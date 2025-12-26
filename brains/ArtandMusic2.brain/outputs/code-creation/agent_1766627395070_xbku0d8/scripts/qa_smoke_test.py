#!/usr/bin/env python3
"""Minimal QA smoke test.

Validates basic runtime assumptions quickly and emits deterministic output for log capture.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = ROOT / "outputs" / "qa" / "exec_logs"


def _stable_print(obj) -> None:
    sys.stdout.write(json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def _run(cmd, timeout=15):
    p = subprocess.run(
        cmd,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
        env=os.environ.copy(),
    )
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def _fs_check():
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    test_file = OUTPUTS_DIR / "smoke_test_write_check.tmp"
    data = "ok\n"
    test_file.write_text(data, encoding="utf-8")
    read_back = test_file.read_text(encoding="utf-8")
    if read_back != data:
        raise RuntimeError("filesystem read/write mismatch")
    test_file.unlink(missing_ok=True)
    return {"outputs_dir": str(OUTPUTS_DIR), "rw_ok": True}
def _docker_check():
    docker_path = shutil.which("docker")
    if not docker_path:
        return {"present": False, "error": "docker_not_found_in_path"}
    rc, out, err = _run(["docker", "version", "--format", "{{.Server.Version}}"], timeout=20)
    if rc != 0:
        return {"present": True, "docker_path": docker_path, "error": "docker_version_failed", "stderr": err[:400]}
    server_version = out.strip() if out.strip() else "unknown"
    rc2, out2, err2 = _run(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=20)
    info_ok = (rc2 == 0)
    return {
        "present": True,
        "docker_path": docker_path,
        "server_version": server_version,
        "docker_info_ok": info_ok,
        "docker_info_stderr": ("" if info_ok else (err2[:400] if err2 else "unknown_error")),
    }
def main() -> int:
    res = {
        "smoke_test": "qa_smoke_test",
        "status": "unknown",
        "python": {
            "executable": sys.executable,
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "cwd": os.getcwd(),
        "root": str(ROOT),
    }

    try:
        res["filesystem"] = _fs_check()
    except Exception as e:
        res["status"] = "fail"
        res["failure"] = {"stage": "filesystem", "error": str(e)}
        _stable_print(res)
        return 10

    res["docker"] = _docker_check()
    if not res["docker"].get("present", False):
        res["status"] = "fail"
        res["failure"] = {"stage": "docker", "error": res["docker"].get("error", "docker_unavailable")}
        _stable_print(res)
        return 20
    if res["docker"].get("error"):
        res["status"] = "fail"
        res["failure"] = {"stage": "docker", "error": res["docker"]["error"], "stderr": res["docker"].get("stderr", "")}
        _stable_print(res)
        return 21

    res["status"] = "ok"
    _stable_print(res)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
