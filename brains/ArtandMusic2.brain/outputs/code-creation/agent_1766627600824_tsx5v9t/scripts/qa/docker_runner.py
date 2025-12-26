from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union
import os
import re
import shlex
import shutil
import subprocess
import time
_CONTAINER_LOST_PATTERNS = [
    r"No such container",
    r"container .* not found",
    r"Error response from daemon: .*not found",
    r"cannot (?:kill|remove) container",
    r"containerd.*(disconnect|unavailable|reset)",
    r"rpc error: code = (?:Unavailable|Unknown)",
    r"transport is closing",
    r"dial unix .*docker\.sock: connect: no such file",
    r"Cannot connect to the Docker daemon",
    r"error during connect",
]
_CONTAINER_LOST_RE = re.compile("|".join(f"(?:{p})" for p in _CONTAINER_LOST_PATTERNS), re.IGNORECASE)
@dataclass(frozen=True)
class DockerRunSpec:
    image: str
    command: Sequence[str]
    workdir: Optional[str] = None
    env: Optional[Dict[str, str]] = None
    mounts: Optional[Sequence[Tuple[str, str]]] = None  # (host, container)
    name: Optional[str] = None
    timeout_s: Optional[int] = None
    stdout_path: Optional[Union[str, Path]] = None
    stderr_path: Optional[Union[str, Path]] = None
    extra_args: Optional[Sequence[str]] = None
@dataclass
class DockerRunResult:
    docker_cmd: List[str]
    exit_code: Optional[int]
    stdout: str
    stderr: str
    timed_out: bool
    duration_s: float
    docker_available: bool
    container_lost: bool

    def as_dict(self) -> Dict[str, object]:
        return {
            "docker_cmd": self.docker_cmd,
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "duration_s": self.duration_s,
            "docker_available": self.docker_available,
            "container_lost": self.container_lost,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }
def docker_available(timeout_s: int = 8) -> bool:
    if not shutil.which("docker"):
        return False
    try:
        p = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout_s,
            check=False,
        )
        return p.returncode == 0
    except Exception:
        return False
def _write_text(path: Optional[Union[str, Path]], text: str) -> None:
    if not path:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", errors="replace")
def _mk_docker_cmd(spec: DockerRunSpec) -> List[str]:
    cmd: List[str] = ["docker", "run", "--rm"]
    if spec.name:
        cmd += ["--name", spec.name]
    if spec.workdir:
        cmd += ["-w", spec.workdir]
    env = dict(spec.env or {})
    for k, v in env.items():
        cmd += ["-e", f"{k}={v}"]
    for host, container in (spec.mounts or ()):
        cmd += ["-v", f"{host}:{container}"]
    if spec.extra_args:
        cmd += list(spec.extra_args)
    cmd.append(spec.image)
    cmd += list(spec.command)
    return cmd
def _looks_like_container_loss(exit_code: Optional[int], stderr: str) -> bool:
    if exit_code is None:
        return True
    if exit_code < 0:
        return True
    if _CONTAINER_LOST_RE.search(stderr or ""):
        return True
    # docker CLI error codes that often indicate daemon/engine issues
    if exit_code in (125, 126, 127) and ("docker" in (stderr or "").lower() or "daemon" in (stderr or "").lower()):
        return True
    return False
def run_in_docker(spec: DockerRunSpec) -> DockerRunResult:
    docker_ok = docker_available()
    docker_cmd = _mk_docker_cmd(spec)

    if not docker_ok:
        msg = "Docker unavailable (missing binary or daemon not reachable)."
        return DockerRunResult(
            docker_cmd=docker_cmd,
            exit_code=None,
            stdout="",
            stderr=msg,
            timed_out=False,
            duration_s=0.0,
            docker_available=False,
            container_lost=True,
        )

    start = time.time()
    proc = subprocess.Popen(
        docker_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=None,
        env={**os.environ},
    )
    out = err = ""
    timed_out = False
    exit_code: Optional[int] = None
    try:
        out, err = proc.communicate(timeout=spec.timeout_s)
        exit_code = proc.returncode
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            proc.kill()
        except Exception:
            pass
        try:
            out2, err2 = proc.communicate(timeout=5)
            out = (out or "") + (out2 or "")
            err = (err or "") + (err2 or "")
        except Exception:
            pass
        exit_code = proc.returncode
    except Exception as e:
        try:
            proc.kill()
        except Exception:
            pass
        err = (err or "") + f"\nRunner exception: {e!r}\n"
        exit_code = proc.returncode
    duration = time.time() - start

    out = out or ""
    err = err or ""
    _write_text(spec.stdout_path, out)
    _write_text(spec.stderr_path, err)

    container_lost = timed_out or _looks_like_container_loss(exit_code, err)
    return DockerRunResult(
        docker_cmd=docker_cmd,
        exit_code=exit_code,
        stdout=out,
        stderr=err,
        timed_out=timed_out,
        duration_s=duration,
        docker_available=True,
        container_lost=container_lost,
    )
def format_docker_cmd(cmd: Sequence[str]) -> str:
    return " ".join(shlex.quote(str(x)) for x in cmd)
