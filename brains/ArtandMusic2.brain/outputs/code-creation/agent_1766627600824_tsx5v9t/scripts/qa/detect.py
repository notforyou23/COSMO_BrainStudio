from __future__ import annotations
import os, platform, re, shutil, subprocess
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

_CONTAINER_LOST_PATTERNS = [
    r"\bcontainer lost\b",
    r"\bno such container\b",
    r"\bcontainer .* (is not running|stopped|exited)\b",
    r"\berror waiting for container\b",
    r"\boci runtime error\b",
    r"\boci runtime exec failed\b",
    r"\brunc did not terminate successfully\b",
    r"\bcontainerd\b.*(disconnect|closed|not found|not running)",
    r"\bcontext canceled\b",
    r"\btransport is closing\b",
    r"\bEOF\b",
    r"\bsignal: killed\b",
    r"\bkilled\b",
]
_DOCKER_UNAVAILABLE_PATTERNS = [
    r"\bcannot connect to the docker daemon\b",
    r"\bis the docker daemon running\b",
    r"\berror during connect\b",
    r"\bconnection refused\b",
    r"\bpermission denied\b.*docker",
    r"\bdocker: command not found\b",
]

@dataclass(frozen=True)
class FailureInfo:
    docker_available: bool
    docker_healthy: bool
    container_lost: bool
    docker_unavailable: bool
    timeout: bool
    exit_code: int
    reason: str
    details: Dict[str, str]
def _run(cmd, timeout: int = 8, env: Optional[dict] = None) -> Tuple[int, str, str, bool]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
        return p.returncode, p.stdout or "", p.stderr or "", False
    except subprocess.TimeoutExpired as e:
        out = (e.stdout.decode("utf-8", "ignore") if isinstance(e.stdout, (bytes, bytearray)) else (e.stdout or ""))
        err = (e.stderr.decode("utf-8", "ignore") if isinstance(e.stderr, (bytes, bytearray)) else (e.stderr or ""))
        return 124, out, err, True
    except Exception as e:
        return 125, "", f"{type(e).__name__}: {e}", False

def _matches_any(text: str, patterns) -> bool:
    t = (text or "").lower()
    return any(re.search(p, t, flags=re.IGNORECASE | re.MULTILINE) for p in patterns)

def docker_cli_present() -> bool:
    return shutil.which("docker") is not None
def docker_healthcheck(timeout: int = 10) -> Dict[str, object]:
    if not docker_cli_present():
        return {"available": False, "healthy": False, "reason": "docker_cli_missing"}

    rc1, out1, err1, to1 = _run(["docker", "version"], timeout=min(6, timeout))
    rc2, out2, err2, to2 = _run(["docker", "info"], timeout=timeout)
    combined = "\n".join([out1, err1, out2, err2]).strip()

    unavailable = _matches_any(combined, _DOCKER_UNAVAILABLE_PATTERNS)
    healthy = (rc1 == 0 and rc2 == 0 and not (to1 or to2) and not unavailable)

    reason = "ok" if healthy else "docker_unhealthy"
    if to1 or to2:
        reason = "docker_timeout"
    elif unavailable:
        reason = "docker_unavailable"
    elif rc1 != 0 or rc2 != 0:
        reason = "docker_error"

    return {
        "available": True,
        "healthy": healthy,
        "reason": reason,
        "exit_codes": {"version": rc1, "info": rc2},
        "stdout": (out1 + "\n" + out2).strip(),
        "stderr": (err1 + "\n" + err2).strip(),
    }
def detect_container_lost(stdout: str = "", stderr: str = "", extra: str = "") -> bool:
    return _matches_any("\n".join([stdout or "", stderr or "", extra or ""]), _CONTAINER_LOST_PATTERNS)

def detect_docker_unavailable(stdout: str = "", stderr: str = "", extra: str = "") -> bool:
    return _matches_any("\n".join([stdout or "", stderr or "", extra or ""]), _DOCKER_UNAVAILABLE_PATTERNS)

def classify_docker_run_failure(exit_code: int, stdout: str = "", stderr: str = "", timeout: bool = False) -> FailureInfo:
    hc = docker_healthcheck(timeout=8)
    docker_avail = bool(hc.get("available"))
    docker_healthy = bool(hc.get("healthy"))

    container_lost = detect_container_lost(stdout, stderr) or (exit_code in (137, 143) and not timeout)
    docker_unavail = (not docker_avail) or detect_docker_unavailable(stdout, stderr) or (not docker_healthy)

    reason = "ok"
    if timeout:
        reason = "timeout"
    elif container_lost:
        reason = "container_lost"
    elif docker_unavail:
        reason = "docker_unavailable"
    elif exit_code != 0:
        reason = "nonzero_exit"

    return FailureInfo(
        docker_available=docker_avail,
        docker_healthy=docker_healthy,
        container_lost=bool(container_lost),
        docker_unavailable=bool(docker_unavail),
        timeout=bool(timeout),
        exit_code=int(exit_code),
        reason=reason,
        details={
            "docker_reason": str(hc.get("reason", "")),
            "docker_stdout": str(hc.get("stdout", ""))[:4000],
            "docker_stderr": str(hc.get("stderr", ""))[:4000],
        },
    )

def should_fallback_to_failsafe(failure: FailureInfo) -> bool:
    return bool(failure.docker_unavailable or failure.container_lost or failure.timeout)

def env_diagnostics() -> Dict[str, str]:
    return {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cwd": os.getcwd(),
        "docker_cli_present": str(docker_cli_present()),
        "ci": str(bool(os.environ.get("CI"))),
    }
