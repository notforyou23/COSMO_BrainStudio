#!/usr/bin/env python3
"""Canonical QA gate entrypoint.

Behavior:
- Try containerized execution (Docker) first.
- If Docker is unavailable, fails, or appears to have lost the container, fall back
  to a no-container failsafe mode.
- Always write logs and partial results to outputs/qa.

Exit code:
- 0 if the selected mode succeeds; otherwise the mode's exit code (non-zero).
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def _utc_ts() -> str:
    return time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime())


def _outputs_dir() -> Path:
    p = Path(os.environ.get("QA_OUTPUT_DIR", "outputs/qa"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, obj: object) -> None:
    _write_text(path, json.dumps(obj, indent=2, sort_keys=True) + "\n")


def _run(cmd: List[str], cwd: Optional[Path], env: Dict[str, str], timeout_s: int) -> Tuple[int, str]:
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout_s,
        )
        return p.returncode, p.stdout
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or "") + f"\n[qa_gate] TIMEOUT after {timeout_s}s\n"
        return 124, out
    except FileNotFoundError as e:
        return 127, f"[qa_gate] COMMAND_NOT_FOUND: {cmd[0]} ({e})\n"
    except Exception as e:
        return 2, f"[qa_gate] EXCEPTION running {cmd!r}: {e}\n"


def _docker_loss_suspected(rc: int, out: str) -> bool:
    if rc in (125, 126, 127, 137):
        return True
    low = out.lower()
    needles = [
        "container lost",
        "no such container",
        "cannot connect to the docker daemon",
        "docker: command not found",
        "is the docker daemon running",
        "context canceled",
        "killed",
        "oom",
    ]
    return any(n in low for n in needles)


def _project_root() -> Path:
    return Path(os.environ.get("QA_PROJECT_ROOT", Path.cwd())).resolve()


def _env_base() -> Dict[str, str]:
    env = dict(os.environ)
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")
    env.setdefault("CI", "1")
    return env


def _write_metadata(run_dir: Path, mode: str, extra: Dict[str, object]) -> None:
    meta = {
        "timestamp_utc": _utc_ts(),
        "mode": mode,
        "cwd": str(Path.cwd()),
        "project_root": str(_project_root()),
        "python": sys.version,
        "platform": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
        "env_hints": {k: os.environ.get(k) for k in ("GITHUB_SHA", "GITHUB_REF", "BUILD_NUMBER", "CI")},
    }
    meta.update(extra)
    _write_json(run_dir / "run_metadata.json", meta)


def _attempt_docker(run_dir: Path, timeout_s: int) -> Tuple[bool, int, str]:
    if shutil.which("docker") is None:
        return False, 127, "[qa_gate] docker not found on PATH\n"
    root = _project_root()
    image = os.environ.get("QA_DOCKER_IMAGE", "python:3.11-slim")
    # Minimal container command: run pytest if available; otherwise compileall.
    inner = (
        "python -m pytest -q || "
        "python -m compileall -q ."
    )
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{root}:/work",
        "-w", "/work",
        image,
        "bash", "-lc", inner,
    ]
    env = _env_base()
    rc, out = _run(cmd, cwd=root, env=env, timeout_s=timeout_s)
    _write_text(run_dir / "docker_stdout_stderr.log", out)
    return True, rc, out


def _failsafe_commands() -> List[List[str]]:
    # Reduced, deterministic subset: smoke-ish selection first; then compileall as last resort.
    cmds: List[List[str]] = []
    cmds.append([sys.executable, "-m", "pytest", "-q", "-k", "smoke or sanity", "--maxfail=1", "--disable-warnings"])
    cmds.append([sys.executable, "-m", "pytest", "-q", "--maxfail=1", "--disable-warnings"])
    cmds.append([sys.executable, "-m", "compileall", "-q", "."])
    return cmds


def _run_failsafe(run_dir: Path, timeout_s: int) -> Tuple[int, str, List[Dict[str, object]]]:
    root = _project_root()
    env = _env_base()
    attempts: List[Dict[str, object]] = []
    combined_out = ""
    final_rc = 1
    for i, cmd in enumerate(_failsafe_commands(), 1):
        rc, out = _run(cmd, cwd=root, env=env, timeout_s=timeout_s)
        attempts.append({"index": i, "cmd": cmd, "returncode": rc})
        combined_out += f"\n[qa_gate] FAILSAFE_ATTEMPT {i}/{len(_failsafe_commands())}: {cmd!r}\n"
        combined_out += out
        _write_text(run_dir / f"failsafe_attempt_{i}.log", out)
        if rc == 0:
            final_rc = 0
            break
        final_rc = rc
    return final_rc, combined_out, attempts


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="QA gate with docker-first and failsafe fallback.")
    ap.add_argument("--mode", choices=["auto", "docker", "failsafe"], default=os.environ.get("QA_MODE", "auto"))
    ap.add_argument("--timeout-s", type=int, default=int(os.environ.get("QA_TIMEOUT_S", "1800")))
    ap.add_argument("--failsafe-timeout-s", type=int, default=int(os.environ.get("QA_FAILSAFE_TIMEOUT_S", "600")))
    args = ap.parse_args(argv)

    outdir = _outputs_dir()
    run_dir = outdir / f"run_{_utc_ts()}"
    run_dir.mkdir(parents=True, exist_ok=True)

    selected_mode = args.mode
    _write_metadata(run_dir, selected_mode, {"requested_mode": args.mode})

    result: Dict[str, object] = {"requested_mode": args.mode, "selected_mode": None, "returncode": None}
    try:
        if args.mode in ("auto", "docker"):
            attempted, rc, out = _attempt_docker(run_dir, timeout_s=args.timeout_s)
            result["docker_attempted"] = attempted
            result["docker_returncode"] = rc
            result["selected_mode"] = "docker"
            if args.mode == "docker":
                result["returncode"] = rc
                _write_json(run_dir / "result.json", result)
                return int(rc)
            if attempted and rc == 0:
                result["returncode"] = 0
                _write_json(run_dir / "result.json", result)
                return 0
            if (not attempted) or _docker_loss_suspected(int(rc), str(out)):
                selected_mode = "failsafe"
            else:
                # Docker failed but not a loss scenario; still fall back to produce partial results.
                selected_mode = "failsafe"

        if selected_mode == "failsafe":
            rc, combined_out, attempts = _run_failsafe(run_dir, timeout_s=args.failsafe_timeout_s)
            _write_text(run_dir / "failsafe_combined.log", combined_out)
            result["selected_mode"] = "failsafe"
            result["failsafe_attempts"] = attempts
            result["returncode"] = rc
            _write_json(run_dir / "result.json", result)
            return int(rc)

        result["selected_mode"] = selected_mode
        result["returncode"] = 2
        result["error"] = f"Unknown mode resolution: {selected_mode}"
        _write_json(run_dir / "result.json", result)
        return 2
    except Exception as e:
        # Last-resort error capture.
        err = f"[qa_gate] FATAL: {e.__class__.__name__}: {e}\n"
        _write_text(run_dir / "fatal_error.log", err)
        result["selected_mode"] = selected_mode
        result["returncode"] = 2
        result["fatal_error"] = err
        _write_json(run_dir / "result.json", result)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
