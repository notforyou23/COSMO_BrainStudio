from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence, Union, Optional, List, Dict, Any
import os
import subprocess
import time


Cmd = Union[str, Sequence[str]]


@dataclass(frozen=True)
class RunResult:
    cmd: List[str]
    cwd: str
    returncode: int
    stdout: str
    stderr: str
    duration_s: float
    timed_out: bool


def _as_argv(cmd: Cmd) -> List[str]:
    if isinstance(cmd, str):
        # Avoid shell=True for determinism/security; allow caller to pass list for args.
        return [cmd]
    return [str(x) for x in cmd]


def _build_env(env_overrides: Optional[Mapping[str, str]] = None) -> Dict[str, str]:
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    if env_overrides:
        for k, v in env_overrides.items():
            if v is None:
                env.pop(k, None)
            else:
                env[str(k)] = str(v)
    return env


def run_command(
    cmd: Cmd,
    cwd: Union[str, os.PathLike, None] = None,
    env_overrides: Optional[Mapping[str, str]] = None,
    timeout_s: Optional[float] = 300.0,
    check: bool = False,
) -> RunResult:
    argv = _as_argv(cmd)
    cwd_str = str(Path(cwd).resolve()) if cwd is not None else str(Path.cwd().resolve())
    env = _build_env(env_overrides)

    t0 = time.time()
    timed_out = False
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd_str,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s if timeout_s is not None else None,
        )
        rc = int(proc.returncode)
        out = proc.stdout or ""
        err = proc.stderr or ""
    except subprocess.TimeoutExpired as e:
        timed_out = True
        rc = 124
        out = (getattr(e, "stdout", None) or "") if isinstance(getattr(e, "stdout", None), str) else ""
        err = (getattr(e, "stderr", None) or "") if isinstance(getattr(e, "stderr", None), str) else ""
        if err:
            err += "\n"
        err += f"Command timed out after {timeout_s}s"
    except FileNotFoundError as e:
        rc = 127
        out = ""
        err = str(e)
    except Exception as e:
        rc = 1
        out = ""
        err = f"{type(e).__name__}: {e}"

    dur = max(0.0, time.time() - t0)
    result = RunResult(
        cmd=argv,
        cwd=cwd_str,
        returncode=rc,
        stdout=out,
        stderr=err,
        duration_s=dur,
        timed_out=timed_out,
    )
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, result.cmd, output=result.stdout, stderr=result.stderr
        )
    return result
