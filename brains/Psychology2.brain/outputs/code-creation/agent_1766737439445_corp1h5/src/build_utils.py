from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import shlex
import subprocess
import sys
import time
from typing import Iterable, Mapping, Sequence


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_dir(project_root: Path) -> Path:
    return ensure_dir(project_root / "_build")


def _cmd_display(cmd: Sequence[str] | str) -> str:
    if isinstance(cmd, str):
        return cmd
    return " ".join(shlex.quote(str(x)) for x in cmd)


@dataclass(frozen=True)
class RunResult:
    name: str
    cmd: str
    returncode: int
    log_path: Path
    duration_s: float


def tee_run(
    *,
    name: str,
    cmd: Sequence[str] | str,
    project_root: Path,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    log_subdir: str = "logs",
    timeout_s: float | None = None,
) -> RunResult:
    bdir = build_dir(project_root)
    log_dir = ensure_dir(bdir / log_subdir)
    log_path = log_dir / f"{name}.log"

    cmd_str = _cmd_display(cmd)
    merged_env = dict(os.environ)
    if env:
        merged_env.update({str(k): str(v) for k, v in env.items()})

    start = time.time()
    with open(log_path, "w", encoding="utf-8") as lf:
        lf.write(f"[step] {name}\n[cmd] {cmd_str}\n[cwd] {cwd or project_root}\n\n")
        lf.flush()
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd or project_root),
            env=merged_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                sys.stdout.write(line)
                lf.write(line)
            rc = proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            proc.kill()
            rc = 124
            msg = f"\n[timeout] Step '{name}' exceeded {timeout_s}s\n"
            sys.stdout.write(msg)
            lf.write(msg)
        duration = time.time() - start
        lf.write(f"\n[exit] {rc}\n[duration_s] {duration:.3f}\n")
        lf.flush()

    if rc != 0:
        raise subprocess.CalledProcessError(rc, cmd_str, output=f"See log: {log_path}")
    return RunResult(name=name, cmd=cmd_str, returncode=rc, log_path=log_path, duration_s=duration)


def validate_artifacts(artifacts: Iterable[Path], *, project_root: Path) -> None:
    missing: list[str] = []
    empty: list[str] = []
    for p in artifacts:
        path = (project_root / p) if not p.is_absolute() else p
        if not path.exists():
            missing.append(str(p))
            continue
        if path.is_dir():
            if not any(path.rglob("*")):
                empty.append(str(p))
            continue
        try:
            if path.stat().st_size <= 0:
                empty.append(str(p))
        except OSError:
            empty.append(str(p))
    if missing or empty:
        parts = []
        if missing:
            parts.append("missing: " + ", ".join(missing))
        if empty:
            parts.append("empty: " + ", ".join(empty))
        raise FileNotFoundError("Required artifact check failed (" + "; ".join(parts) + ")")
