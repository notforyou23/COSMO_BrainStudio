from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import sys
import subprocess
from datetime import datetime, timezone
from typing import Optional, Mapping, Any, Iterable, Tuple


def canonical_repo_root(start: Optional[Path] = None) -> Path:
    p = (start or Path.cwd()).resolve()
    candidates = [p] + list(p.parents)
    markers = ("pyproject.toml", "setup.cfg", "requirements.txt", ".git")
    for d in candidates:
        if any((d / m).exists() for m in markers):
            return d.resolve()
    for d in candidates:
        if (d / "scripts").is_dir() and (d / "outputs").exists():
            return d.resolve()
    return p.resolve()


def _iter_init_outputs_candidates(repo_root: Path) -> Iterable[Path]:
    base = repo_root / "runtime" / "outputs" / "code-creation"
    if not base.exists():
        return []
    return base.rglob("init_outputs.py")


def find_newest_init_outputs_py(repo_root: Optional[Path] = None) -> Path:
    root = canonical_repo_root(repo_root)
    cands = [p for p in _iter_init_outputs_candidates(root) if p.is_file()]
    if not cands:
        raise FileNotFoundError(f"No init_outputs.py found under {root/'runtime/outputs/code-creation'}")
    def key(p: Path) -> Tuple[float, str]:
        try:
            mt = p.stat().st_mtime
        except OSError:
            mt = -1.0
        return (mt, str(p))
    return max(cands, key=key).resolve()


def deterministic_timestamp(dt: Optional[datetime] = None) -> str:
    d = dt or datetime.now(timezone.utc)
    d = d.astimezone(timezone.utc)
    ms = int(d.microsecond / 1000)
    return d.strftime("%Y-%m-%dT%H-%M-%S-") + f"{ms:03d}Z"


def ensure_outputs_qa_dir(repo_root: Optional[Path] = None) -> Path:
    root = canonical_repo_root(repo_root)
    out = (root / "outputs" / "qa")
    out.mkdir(parents=True, exist_ok=True)
    return out.resolve()


def qa_log_path(repo_root: Optional[Path] = None, prefix: str = "init_outputs", ts: Optional[str] = None) -> Path:
    out = ensure_outputs_qa_dir(repo_root)
    stamp = ts or deterministic_timestamp()
    safe_prefix = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in prefix).strip("_") or "log"
    return (out / f"{stamp}_{safe_prefix}.log").resolve()


@dataclass(frozen=True)
class RunResult:
    returncode: int
    stdout: str
    stderr: str
    cmd: Tuple[str, ...]
    cwd: str
    duration_s: float


def run_python_file_capture(py_file: Path, cwd: Optional[Path] = None, env: Optional[Mapping[str, str]] = None, timeout: Optional[float] = None) -> RunResult:
    import time
    py_path = Path(py_file).resolve()
    if not py_path.is_file():
        raise FileNotFoundError(str(py_path))
    run_cwd = str((cwd or py_path.parent).resolve())
    cmd = (sys.executable, str(py_path))
    merged_env = os.environ.copy()
    if env:
        merged_env.update({str(k): str(v) for k, v in env.items()})
    t0 = time.time()
    p = subprocess.run(cmd, cwd=run_cwd, env=merged_env, capture_output=True, text=True, timeout=timeout)
    dt = time.time() - t0
    return RunResult(returncode=p.returncode, stdout=p.stdout or "", stderr=p.stderr or "", cmd=cmd, cwd=run_cwd, duration_s=dt)


def write_run_log(log_path: Path, result: RunResult, header: Optional[Mapping[str, Any]] = None) -> Path:
    lp = Path(log_path).resolve()
    lp.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    if header:
        for k, v in header.items():
            lines.append(f"{k}: {v}")
    lines.extend([
        f"cmd: {' '.join(result.cmd)}",
        f"cwd: {result.cwd}",
        f"returncode: {result.returncode}",
        f"duration_s: {result.duration_s:.3f}",
        "",
        "---- STDOUT ----",
        result.stdout.rstrip("\n"),
        "",
        "---- STDERR ----",
        result.stderr.rstrip("\n"),
        "",
    ])
    lp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return lp
