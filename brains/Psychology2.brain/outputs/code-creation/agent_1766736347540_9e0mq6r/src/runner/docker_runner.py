from __future__ import annotations
import os
import shlex
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union
def _ts() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _popen(cmd: Sequence[str], **kwargs) -> subprocess.Popen:
    return subprocess.Popen(list(cmd), **kwargs)


def _run(cmd: Sequence[str], timeout: Optional[float] = None) -> Tuple[int, str, str]:
    p = _popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        out, err = p.communicate()
        return 124, out, err
    return p.returncode, out, err


def _is_missing_container(stderr: str) -> bool:
    s = (stderr or "").lower()
    return "no such container" in s or "no such object" in s or "could not find" in s
@dataclass
class DockerRunResult:
    container_id: Optional[str]
    container_name: Optional[str]
    start_time_utc: str
    end_time_utc: str
    exit_code: Optional[int]
    status: str
    container_lost: bool
    container_lost_at_utc: Optional[str]
    docker_error: Optional[str]
    metadata: Dict[str, object]
class DockerRunner:
    """Docker execution backend using the local docker CLI.

    Provides robust log streaming and explicit detection of container disappearance.
    """

    def __init__(self, docker_bin: str = "docker") -> None:
        self.docker_bin = docker_bin

    def _docker(self, *args: str) -> List[str]:
        return [self.docker_bin, *args]

    def run(
        self,
        image: str,
        command: Union[str, Sequence[str]],
        log_path: Union[str, Path],
        *,
        name: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        workdir: Optional[str] = None,
        mounts: Optional[Sequence[Tuple[str, str, str]]] = None,
        network: Optional[str] = None,
        timeout_s: Optional[float] = None,
        remove: bool = False,
        extra_args: Optional[Sequence[str]] = None,
    ) -> DockerRunResult:
        log_path = Path(log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        start = _ts()
        container_id: Optional[str] = None
        exit_code: Optional[int] = None
        status = "unknown"
        lost = False
        lost_at: Optional[str] = None
        docker_error: Optional[str] = None
        meta: Dict[str, object] = {"image": image, "command": command}

        args: List[str] = ["run", "-d"]
        if name:
            args += ["--name", name]
        if workdir:
            args += ["-w", workdir]
        if network:
            args += ["--network", network]
        if remove:
            args.append("--rm")
        if env:
            for k, v in env.items():
                args += ["-e", f"{k}={v}"]
        if mounts:
            for src, dst, mode in mounts:
                args += ["-v", f"{src}:{dst}:{mode}"]
        if extra_args:
            args += list(extra_args)
        args.append(image)
        if isinstance(command, str):
            args += ["sh", "-lc", command]
        else:
            args += list(command)

        rc, out, err = _run(self._docker(*args))
        if rc != 0:
            end = _ts()
            docker_error = (err or out or "").strip() or f"docker run failed rc={rc}"
            return DockerRunResult(
                container_id=None,
                container_name=name,
                start_time_utc=start,
                end_time_utc=end,
                exit_code=None,
                status="docker_error",
                container_lost=False,
                container_lost_at_utc=None,
                docker_error=docker_error,
                metadata=meta,
            )

        container_id = (out or "").strip() or None
        meta["container_id"] = container_id

        stop_event = threading.Event()
        log_err: List[str] = []

        def _follow_logs() -> None:
            cmd = self._docker("logs", "-f", "--timestamps", container_id or "")
            try:
                with open(log_path, "a", encoding="utf-8", errors="replace") as f:
                    p = _popen(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
                    while True:
                        if stop_event.is_set():
                            break
                        if p.poll() is not None:
                            break
                        time.sleep(0.1)
                    if p.poll() is None:
                        p.terminate()
                        try:
                            p.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            p.kill()
                    if p.stderr:
                        e = p.stderr.read() if hasattr(p.stderr, "read") else ""
                        if e:
                            log_err.append(e)
            except Exception as e:
                log_err.append(str(e))

        t = threading.Thread(target=_follow_logs, name="docker-logs", daemon=True)
        t.start()

        deadline = (time.time() + timeout_s) if timeout_s else None
        wait_rc = None
        while True:
            if deadline and time.time() > deadline:
                _run(self._docker("kill", container_id or ""))
                status = "timeout_killed"
                break
            rc, out, err = _run(self._docker("wait", container_id or ""), timeout=1.0)
            if rc == 0:
                try:
                    exit_code = int((out or "").strip())
                except Exception:
                    exit_code = None
                status = "exited"
                wait_rc = 0
                break
            if rc == 124:
                pass
            else:
                if _is_missing_container(err):
                    lost = True
                    lost_at = _ts()
                    status = "container_lost"
                    docker_error = (err or "").strip() or "container lost during wait"
                    break
                wait_rc = rc
                docker_error = (err or out or "").strip()
                status = "docker_error"
                break
            rc2, _o2, e2 = _run(self._docker("inspect", container_id or ""), timeout=1.0)
            if rc2 != 0 and _is_missing_container(e2):
                lost = True
                lost_at = _ts()
                status = "container_lost"
                docker_error = (e2 or "").strip() or "container lost during inspect"
                break

        stop_event.set()
        t.join(timeout=3)

        if not remove and container_id and status in {"exited", "timeout_killed"}:
            rc3, out3, err3 = _run(self._docker("inspect", container_id), timeout=2.0)
            if rc3 == 0:
                meta["inspect_json"] = out3
            elif _is_missing_container(err3):
                lost = True
                lost_at = lost_at or _ts()
                status = "container_lost"
                docker_error = docker_error or (err3 or "").strip()

        if remove and container_id and not lost:
            _run(self._docker("rm", "-f", container_id), timeout=5.0)

        end = _ts()
        if log_err and not docker_error:
            meta["log_stderr"] = "".join(log_err).strip()

        return DockerRunResult(
            container_id=container_id,
            container_name=name,
            start_time_utc=start,
            end_time_utc=end,
            exit_code=exit_code,
            status=status,
            container_lost=lost,
            container_lost_at_utc=lost_at,
            docker_error=docker_error,
            metadata=meta,
        )
