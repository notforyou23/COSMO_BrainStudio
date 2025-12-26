"""Docker integration helpers for the QA runner.

Provides:
- docker availability detection (binary + daemon)
- robust container invocation with log capture
- explicit error classification so the caller can trigger failsafe mode
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import os
import shutil
import subprocess
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union


class DockerErrorKind(str, Enum):
    OK = "ok"
    DOCKER_MISSING = "docker_missing"
    DAEMON_UNAVAILABLE = "daemon_unavailable"
    PERMISSION_DENIED = "permission_denied"
    IMAGE_NOT_FOUND = "image_not_found"
    PULL_FAILED = "pull_failed"
    CONTAINER_FAILED = "container_failed"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class DockerAvailability:
    ok: bool
    kind: DockerErrorKind
    detail: str = ""


@dataclass(frozen=True)
class DockerRunResult:
    ok: bool
    kind: DockerErrorKind
    returncode: int
    stdout: str
    stderr: str
    cmd: List[str]
    detail: str = ""


def _run_capture(cmd: Sequence[str], timeout_s: Optional[float] = None) -> Tuple[int, str, str]:
    p = subprocess.run(
        list(cmd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout_s,
        check=False,
    )
    return p.returncode, p.stdout or "", p.stderr or ""


def docker_available(timeout_s: float = 4.0) -> DockerAvailability:
    if shutil.which("docker") is None:
        return DockerAvailability(False, DockerErrorKind.DOCKER_MISSING, "docker executable not found on PATH")
    try:
        rc, out, err = _run_capture(["docker", "info"], timeout_s=timeout_s)
    except subprocess.TimeoutExpired:
        return DockerAvailability(False, DockerErrorKind.DAEMON_UNAVAILABLE, "docker info timed out")
    except Exception as e:
        return DockerAvailability(False, DockerErrorKind.UNKNOWN, f"docker info failed: {e}")
    if rc == 0:
        return DockerAvailability(True, DockerErrorKind.OK, "")
    kind, detail = classify_docker_failure(rc, out, err)
    if kind in (DockerErrorKind.PERMISSION_DENIED, DockerErrorKind.DOCKER_MISSING):
        return DockerAvailability(False, kind, detail)
    return DockerAvailability(False, DockerErrorKind.DAEMON_UNAVAILABLE, detail)


def classify_docker_failure(returncode: int, stdout: str = "", stderr: str = "", exc: Optional[BaseException] = None) -> Tuple[DockerErrorKind, str]:
    if isinstance(exc, subprocess.TimeoutExpired):
        return DockerErrorKind.TIMEOUT, "docker command timed out"
    if isinstance(exc, FileNotFoundError):
        return DockerErrorKind.DOCKER_MISSING, "docker executable not found"
    msg = (stderr or "") + "\n" + (stdout or "")
    m = msg.lower()
    if "permission denied" in m or "got permission denied" in m or "access is denied" in m:
        return DockerErrorKind.PERMISSION_DENIED, (stderr or stdout or "permission denied").strip()
    if "cannot connect to the docker daemon" in m or "is the docker daemon running" in m or "error during connect" in m:
        return DockerErrorKind.DAEMON_UNAVAILABLE, (stderr or stdout or "daemon unavailable").strip()
    if "no such image" in m:
        return DockerErrorKind.IMAGE_NOT_FOUND, (stderr or stdout or "image not found").strip()
    if "pull access denied" in m or "requested access to the resource is denied" in m or "authentication required" in m:
        return DockerErrorKind.PULL_FAILED, (stderr or stdout or "pull failed").strip()
    if returncode == 0:
        return DockerErrorKind.OK, ""
    if "not found" in m and ("manifest" in m or "repository" in m):
        return DockerErrorKind.PULL_FAILED, (stderr or stdout or "pull failed").strip()
    return DockerErrorKind.CONTAINER_FAILED, (stderr or stdout or f"docker failed rc={returncode}").strip()


def build_docker_run_cmd(
    image: str,
    inner_cmd: Sequence[str],
    *,
    workdir_host: Union[str, Path],
    workdir_container: str = "/work",
    mounts: Optional[Dict[Union[str, Path], str]] = None,
    env: Optional[Dict[str, str]] = None,
    user: Optional[str] = None,
    network: Optional[str] = None,
) -> List[str]:
    cmd: List[str] = ["docker", "run", "--rm"]
    if user:
        cmd += ["--user", user]
    if network:
        cmd += ["--network", network]
    cmd += ["-w", workdir_container]
    cmd += ["-v", f"{Path(workdir_host).resolve()}:{workdir_container}"]
    if mounts:
        for host, cont in mounts.items():
            cmd += ["-v", f"{Path(host).resolve()}:{cont}"]
    if env:
        for k, v in env.items():
            cmd += ["-e", f"{k}={v}"]
    cmd.append(image)
    cmd.extend(list(inner_cmd))
    return cmd


def run_docker(
    image: str,
    inner_cmd: Sequence[str],
    *,
    workdir_host: Union[str, Path],
    workdir_container: str = "/work",
    mounts: Optional[Dict[Union[str, Path], str]] = None,
    env: Optional[Dict[str, str]] = None,
    timeout_s: Optional[float] = None,
    log_path: Optional[Union[str, Path]] = None,
    user: Optional[str] = None,
    network: Optional[str] = None,
) -> DockerRunResult:
    cmd = build_docker_run_cmd(
        image,
        inner_cmd,
        workdir_host=workdir_host,
        workdir_container=workdir_container,
        mounts=mounts,
        env=env,
        user=user,
        network=network,
    )
    try:
        p = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_s,
            check=False,
            env=os.environ.copy(),
        )
        stdout, stderr, rc = p.stdout or "", p.stderr or "", int(p.returncode)
        kind, detail = classify_docker_failure(rc, stdout, stderr)
    except BaseException as e:
        kind, detail = classify_docker_failure(1, "", "", exc=e)
        stdout, stderr, rc = "", (str(e) or repr(e)), 1
    if log_path is not None:
        lp = Path(log_path)
        lp.parent.mkdir(parents=True, exist_ok=True)
        lp.write_text(
            "CMD: " + " ".join(cmd) + "\n\nSTDOUT:\n" + stdout + "\n\nSTDERR:\n" + stderr + "\n",
            encoding="utf-8",
        )
    return DockerRunResult(kind == DockerErrorKind.OK, kind, rc, stdout, stderr, cmd, detail)


def should_fallback_to_failsafe(kind: DockerErrorKind) -> bool:
    return kind in (
        DockerErrorKind.DOCKER_MISSING,
        DockerErrorKind.DAEMON_UNAVAILABLE,
        DockerErrorKind.PERMISSION_DENIED,
        DockerErrorKind.TIMEOUT,
    )
