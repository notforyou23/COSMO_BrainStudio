#!/usr/bin/env python3
\"\"\"record_versions.py

Utility to capture Python/OS/tooling versions and emit structured JSON.
Designed for inclusion in incident reports and CI diagnostics.

Usage:
  python scripts/record_versions.py --output runtime/_build/incident_reports/.../versions.json
  python scripts/record_versions.py  (prints JSON to stdout)
\"\"\"
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence


@dataclass
class CmdResult:
    argv: Sequence[str]
    ok: bool
    returncode: int
    duration_ms: int
    stdout: str
    stderr: str
    which: Optional[str] = None


def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())


def run_cmd(argv: Sequence[str], timeout_s: int = 10) -> CmdResult:
    t0 = time.time()
    exe = shutil.which(argv[0]) if argv else None
    try:
        p = subprocess.run(
            list(argv),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_s,
            check=False,
            env=os.environ.copy(),
        )
        ok = p.returncode == 0
        out, err = p.stdout.strip(), p.stderr.strip()
        rc = p.returncode
    except FileNotFoundError:
        ok, out, err, rc = False, "", f"not found: {argv[0]}", 127
    except subprocess.TimeoutExpired as e:
        ok = False
        out = (e.stdout or "").strip() if isinstance(e.stdout, str) else ""
        err = (e.stderr or "").strip() if isinstance(e.stderr, str) else ""
        err = (err + "\n" if err else "") + f"timeout after {timeout_s}s"
        rc = 124
    except Exception as e:
        ok, out, err, rc = False, "", f"exception: {type(e).__name__}: {e}", 1
    dt = int((time.time() - t0) * 1000)
    return CmdResult(argv=tuple(argv), ok=ok, returncode=rc, duration_ms=dt, stdout=out, stderr=err, which=exe)


def _python_info() -> Dict[str, Any]:
    return {
        "executable": sys.executable,
        "version": sys.version,
        "version_info": list(sys.version_info),
        "prefix": sys.prefix,
        "base_prefix": getattr(sys, "base_prefix", None),
        "implementation": platform.python_implementation(),
        "compiler": platform.python_compiler(),
        "build": platform.python_build(),
        "argv0": sys.argv[0] if sys.argv else None,
        "path0": sys.path[0] if sys.path else None,
    }


def _platform_info() -> Dict[str, Any]:
    return {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "architecture": list(platform.architecture()),
        "uname": list(platform.uname()),
        "python_build": platform.python_build(),
        "python_branch": getattr(platform, "python_branch", lambda: None)(),
        "python_revision": getattr(platform, "python_revision", lambda: None)(),
    }


def _tooling() -> Dict[str, Any]:
    cmds = {
        "python": [sys.executable, "--version"],
        "pip": [sys.executable, "-m", "pip", "--version"],
        "pip_list": [sys.executable, "-m", "pip", "list", "--format=json"],
        "git": ["git", "--version"],
        "docker": ["docker", "--version"],
        "docker_compose": ["docker", "compose", "version"],
        "uname": ["uname", "-a"],
    }
    out: Dict[str, Any] = {}
    for k, argv in cmds.items():
        r = run_cmd(argv, timeout_s=20 if k == "pip_list" else 10)
        d = asdict(r)
        if k == "pip_list" and r.ok and r.stdout:
            try:
                d["parsed_json"] = json.loads(r.stdout)
            except Exception:
                d["parsed_json"] = None
        out[k] = d
    return out


def collect_versions(extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    doc = {
        "schema_version": 1,
        "collected_at_utc": _ts(),
        "cwd": os.getcwd(),
        "env": {
            "ci": os.environ.get("CI"),
            "github_actions": os.environ.get("GITHUB_ACTIONS"),
            "runner_os": os.environ.get("RUNNER_OS"),
            "runner_arch": os.environ.get("RUNNER_ARCH"),
            "pythonpath": os.environ.get("PYTHONPATH"),
            "path": os.environ.get("PATH"),
        },
        "python": _python_info(),
        "platform": _platform_info(),
        "tooling": _tooling(),
    }
    if extra:
        doc["extra"] = extra
    return doc


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Capture Python/OS/tooling versions as JSON.")
    p.add_argument("--output", "-o", type=str, default="", help="Write JSON to this path (otherwise stdout).")
    p.add_argument("--extra", type=str, default="", help="Optional JSON object to merge under 'extra'.")
    args = p.parse_args(list(argv) if argv is not None else None)

    extra_obj: Optional[Dict[str, Any]] = None
    if args.extra:
        try:
            extra_obj = json.loads(args.extra)
            if not isinstance(extra_obj, dict):
                extra_obj = {"_extra": extra_obj}
        except Exception as e:
            extra_obj = {"_extra_parse_error": f"{type(e).__name__}: {e}", "_extra_raw": args.extra}

    data = collect_versions(extra=extra_obj)
    if args.output:
        _write_json(Path(args.output), data)
    else:
        sys.stdout.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
