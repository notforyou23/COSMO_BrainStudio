"""Lightweight Docker health checks for gate scripts.

Design goals:
- Fast, minimal side effects by default (no pull/run unless requested).
- Actionable diagnostics for daemon reachability, PATH issues, and permissions.
- Pure stdlib; safe to import in validators.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union


@dataclass
class Check:
    name: str
    ok: bool
    summary: str
    details: str = ""
    hint: str = ""


def _run(cmd: Sequence[str], timeout: float = 8.0, env: Optional[Dict[str, str]] = None) -> Tuple[int, str, str, float]:
    """Run a command, returning (rc, stdout, stderr, seconds)."""
    t0 = time.time()
    try:
        p = subprocess.run(
            list(cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip(), time.time() - t0
    except FileNotFoundError:
        return 127, "", f"not found: {cmd[0]}", time.time() - t0
    except subprocess.TimeoutExpired as e:
        out = (getattr(e, "stdout", "") or "").strip()
        err = (getattr(e, "stderr", "") or "").strip()
        return 124, out, (err or "timeout"), time.time() - t0
    except Exception as e:
        return 1, "", f"{type(e).__name__}: {e}", time.time() - t0


def _sock_path() -> Optional[Path]:
    # Default for Linux, plus common alternative.
    for p in ("/var/run/docker.sock", "/run/docker.sock"):
        sp = Path(p)
        if sp.exists():
            return sp
    return None


def _docker_cmd() -> Optional[str]:
    return shutil.which("docker")


def docker_healthcheck(
    *,
    allow_pull_run: Optional[bool] = None,
    image: str = "hello-world",
    timeout: float = 8.0,
) -> Dict[str, Union[bool, str, List[Dict[str, str]]]]:
    """Return a structured docker health report.

    allow_pull_run:
      - None: enabled only if DOCKER_HEALTHCHECK_PULLRUN=1/true/yes
      - False: never pull/run (default behavior)
      - True: attempt pull+run (may be slower and have side effects)
    """
    env_flag = os.environ.get("DOCKER_HEALTHCHECK_PULLRUN", "").strip().lower()
    if allow_pull_run is None:
        allow_pull_run = env_flag in {"1", "true", "yes", "y", "on"}

    checks: List[Check] = []
    sysname = platform.system()
    dock = _docker_cmd()
    if not dock:
        checks.append(
            Check(
                name="docker_in_path",
                ok=False,
                summary="docker CLI not found on PATH",
                details=f"PATH={os.environ.get('PATH','')}",
                hint="Install Docker Desktop/Engine and ensure `docker` is on PATH.",
            )
        )
        return {"ok": False, "platform": sysname, "docker_path": "", "checks": [asdict(c) for c in checks]}

    checks.append(Check(name="docker_in_path", ok=True, summary=f"docker CLI found: {dock}"))

    rc, out, err, secs = _run([dock, "version", "--format", "{{.Server.Version}}"], timeout=timeout)
    if rc == 0 and out:
        checks.append(Check(name="docker_version", ok=True, summary=f"daemon reachable (server {out})", details=f"{secs:.2f}s"))
    else:
        details = (err or out or "").strip()
        hint = "Start Docker Desktop/daemon. On Linux, ensure user is in the docker group or run with appropriate permissions."
        if "Cannot connect to the Docker daemon" in details:
            hint = "Docker daemon not reachable. Start it and re-run. Check DOCKER_HOST/contexts if configured."
        checks.append(Check(name="docker_version", ok=False, summary="daemon not reachable via `docker version`", details=details, hint=hint))

    # Permission/socket hints (best-effort; safe on non-Linux too)
    sp = _sock_path()
    if sp:
        try:
            st = sp.stat()
            mode = st.st_mode & 0o777
            readable = os.access(str(sp), os.R_OK)
            writable = os.access(str(sp), os.W_OK)
            ok = readable and writable
            hint = ""
            if sysname == "Linux" and not ok:
                hint = "No access to docker socket; add user to `docker` group or run with elevated permissions."
            checks.append(
                Check(
                    name="docker_socket_access",
                    ok=ok,
                    summary=f"socket {sp} access: r={readable} w={writable} mode={oct(mode)}",
                    details=f"uid={getattr(st,'st_uid',-1)} gid={getattr(st,'st_gid',-1)}",
                    hint=hint,
                )
            )
        except Exception as e:
            checks.append(Check(name="docker_socket_access", ok=False, summary=f"socket {sp} stat failed", details=f"{type(e).__name__}: {e}"))
    else:
        checks.append(Check(name="docker_socket_access", ok=True, summary="docker socket path not detected (may be non-Linux/remote context)"))

    # Context info can explain mismatches.
    rc, out, err, _ = _run([dock, "context", "show"], timeout=timeout)
    if rc == 0 and out:
        checks.append(Check(name="docker_context", ok=True, summary=f"context: {out}"))
    else:
        checks.append(Check(name="docker_context", ok=True, summary="context: unavailable", details=(err or out).strip()))

    # Optional pull+run sanity check (can catch hung engine or broken networking)
    if allow_pull_run:
        rc, out, err, secs = _run([dock, "run", "--rm", image], timeout=max(timeout, 20.0))
        ok = (rc == 0)
        details = "\n".join(x for x in [out, err] if x).strip()
        hint = ""
        if not ok:
            hint = "Try `docker info` and check networking/proxy settings; ensure sufficient disk space and permissions."
        checks.append(Check(name="docker_run_sanity", ok=ok, summary=f"docker run --rm {image} (rc={rc})", details=f"{secs:.2f}s\n{details}".strip(), hint=hint))
    else:
        checks.append(Check(name="docker_run_sanity", ok=True, summary="skipped (set DOCKER_HEALTHCHECK_PULLRUN=1 to enable)"))

    overall_ok = all(c.ok for c in checks if c.name in {"docker_in_path", "docker_version"}) and any(
        c.ok for c in checks if c.name == "docker_in_path"
    )
    return {"ok": bool(overall_ok), "platform": sysname, "docker_path": dock or "", "checks": [asdict(c) for c in checks]}


def format_health_report(report: Dict[str, Union[bool, str, List[Dict[str, str]]]]) -> str:
    """Format a docker health report as human-readable text."""
    lines: List[str] = []
    lines.append(f"Docker healthcheck: ok={report.get('ok')}")
    lines.append(f"platform={report.get('platform')} docker={report.get('docker_path')}")
    for c in report.get("checks", []) or []:
        name = c.get("name", "")
        ok = c.get("ok", False)
        summary = c.get("summary", "")
        lines.append(f"- [{ 'OK' if ok else 'FAIL' }] {name}: {summary}")
        details = (c.get("details") or "").strip()
        if details:
            lines.append(f"    details: {details.replace(chr(10), ' | ')}")
        hint = (c.get("hint") or "").strip()
        if hint and not ok:
            lines.append(f"    hint: {hint}")
    return "\n".join(lines).rstrip() + "\n"
