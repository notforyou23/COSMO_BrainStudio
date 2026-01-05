from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence, Optional, Union
import os
import shlex
import subprocess
import time
Cmd = Union[Sequence[str], str]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_env_subset(env: Optional[Mapping[str, str]], allow: Optional[Sequence[str]]) -> Optional[dict[str, str]]:
    if env is None:
        return None
    if not allow:
        return None
    out: dict[str, str] = {}
    for k in allow:
        if k in env:
            out[k] = str(env[k])
    return out
@dataclass(frozen=True)
class RunResult:
    command: list[str]
    command_str: str
    cwd: str
    start_utc: str
    end_utc: str
    duration_s: float
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool
    timeout_s: Optional[float] = None
    env_subset: Optional[dict[str, str]] = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["ok"] = (self.returncode == 0) and (not self.timed_out)
        return d
def run_command(
    cmd: Cmd,
    *,
    cwd: Optional[Union[str, os.PathLike[str]]] = None,
    env: Optional[Mapping[str, str]] = None,
    timeout_s: Optional[float] = None,
    check: bool = False,
    shell: bool = False,
    text: bool = True,
    encoding: str = "utf-8",
    errors: str = "replace",
    env_allowlist: Optional[Sequence[str]] = None,
) -> RunResult:
    """Run a subprocess while capturing stdout/stderr, exit code, timing, and metadata.

    Args:
        cmd: Sequence of args (preferred) or string (only if shell=True or already tokenized).
        cwd: Working directory for the command.
        env: Environment mapping; if None inherits parent environment.
        timeout_s: Timeout in seconds.
        check: If True, raises CalledProcessError on non-zero exit codes (after capture).
        shell: If True, executes through the shell (use sparingly).
        text/encoding/errors: Text decode options.
        env_allowlist: If provided, records only these env vars in env_subset for logging.
    """
    start_utc = _utc_now_iso()
    t0 = time.perf_counter()
    cwd_str = os.fspath(cwd) if cwd is not None else os.getcwd()

    if shell:
        if isinstance(cmd, (list, tuple)):
            cmd_str = " ".join(shlex.quote(str(x)) for x in cmd)
        else:
            cmd_str = str(cmd)
        cmd_list = [cmd_str]
    else:
        if isinstance(cmd, str):
            cmd_list = shlex.split(cmd)
        else:
            cmd_list = [str(x) for x in cmd]
        cmd_str = " ".join(shlex.quote(x) for x in cmd_list)

    timed_out = False
    stdout = ""
    stderr = ""
    returncode = 0

    try:
        proc = subprocess.run(
            cmd if shell else cmd_list,
            cwd=cwd_str,
            env=None if env is None else dict(env),
            capture_output=True,
            text=text,
            encoding=encoding if text else None,
            errors=errors if text else None,
            timeout=timeout_s,
            shell=shell,
            check=False,
        )
        stdout = proc.stdout if proc.stdout is not None else ""
        stderr = proc.stderr if proc.stderr is not None else ""
        returncode = int(proc.returncode)
    except subprocess.TimeoutExpired as e:
        timed_out = True
        stdout = e.stdout if isinstance(e.stdout, str) else (e.stdout.decode(encoding, errors) if e.stdout else "")
        stderr = e.stderr if isinstance(e.stderr, str) else (e.stderr.decode(encoding, errors) if e.stderr else "")
        returncode = 124
    finally:
        t1 = time.perf_counter()
        end_utc = _utc_now_iso()

    res = RunResult(
        command=cmd_list if not shell else (cmd_list if isinstance(cmd_list, list) else [cmd_str]),
        command_str=cmd_str,
        cwd=cwd_str,
        start_utc=start_utc,
        end_utc=end_utc,
        duration_s=round(t1 - t0, 6),
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
        timeout_s=timeout_s,
        env_subset=_safe_env_subset(env, env_allowlist),
    )

    if check and ((res.returncode != 0) or res.timed_out):
        raise subprocess.CalledProcessError(
            res.returncode,
            cmd=res.command_str if shell else res.command,
            output=res.stdout,
            stderr=res.stderr,
        )
    return res
