from __future__ import annotations
from pathlib import Path
import os, sys, shlex, subprocess, datetime
from typing import Iterable, Optional, Dict, List, Union

ROOT = Path(__file__).resolve().parents[1]

def _ts() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def ensure_build_dir(root: Optional[Path] = None, clean: bool = False) -> Path:
    root = (root or ROOT).resolve()
    b = root / "_build"
    if clean and b.exists():
        for p in sorted(b.rglob("*"), reverse=True):
            if p.is_file() or p.is_symlink():
                p.unlink(missing_ok=True)
            elif p.is_dir():
                try:
                    p.rmdir()
                except OSError:
                    pass
    (b / "logs").mkdir(parents=True, exist_ok=True)
    return b

def _coerce_cmd(cmd: Union[str, Iterable[str]]) -> List[str]:
    if isinstance(cmd, str):
        return shlex.split(cmd)
    return list(cmd)

def run_step(
    name: str,
    cmd: Union[str, Iterable[str]],
    build_dir: Optional[Path] = None,
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    timeout: Optional[float] = None,
) -> Path:
    build_dir = ensure_build_dir(build_dir or ROOT)
    step_dir = build_dir / name
    step_dir.mkdir(parents=True, exist_ok=True)
    log_path = build_dir / "logs" / f"{name}.log"

    merged_env = os.environ.copy()
    merged_env.update({
        "BUILD_DIR": str(build_dir),
        "STEP_BUILD_DIR": str(step_dir),
        "PYTHONUNBUFFERED": "1",
    })
    if env:
        merged_env.update(env)

    cmd_list = _coerce_cmd(cmd)
    header = f"[{_ts()}] [{name}] RUN: {subprocess.list2cmdline(cmd_list)}\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(header)
        f.flush()
        sys.stdout.write(header)
        sys.stdout.flush()

        p = subprocess.Popen(
            cmd_list,
            cwd=str((cwd or ROOT).resolve()),
            env=merged_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
        try:
            assert p.stdout is not None
            for line in p.stdout:
                stamped = f"[{_ts()}] [{name}] {line}"
                sys.stdout.write(stamped)
                f.write(stamped)
            rc = p.wait(timeout=timeout)
        except Exception:
            p.kill()
            rc = p.wait()
            raise
    if rc != 0:
        raise subprocess.CalledProcessError(rc, cmd_list, output=f"See log: {log_path}")
    return step_dir

def _env_cmd(var: str) -> Optional[List[str]]:
    v = os.environ.get(var, "").strip()
    return _coerce_cmd(v) if v else None

def step_artifact_gate(build_dir: Optional[Path] = None) -> Path:
    cmd = _env_cmd("ARTIFACT_GATE_CMD") or [sys.executable, "-m", "scripts.artifact_gate"]
    return run_step("artifact_gate", cmd, build_dir=build_dir)

def step_taxonomy_validation(build_dir: Optional[Path] = None) -> Path:
    cmd = _env_cmd("TAXONOMY_VALIDATE_CMD") or [sys.executable, "-m", "scripts.taxonomy_validate"]
    return run_step("taxonomy_validation", cmd, build_dir=build_dir)

def step_meta_analysis_demo(build_dir: Optional[Path] = None) -> Path:
    cmd = _env_cmd("META_ANALYSIS_DEMO_CMD") or [sys.executable, "-m", "scripts.toy_meta_analysis_demo"]
    return run_step("meta_analysis_demo", cmd, build_dir=build_dir)
