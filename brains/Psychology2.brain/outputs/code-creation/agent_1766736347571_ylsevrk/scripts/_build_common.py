from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
import subprocess
import time
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

Pathish = Union[str, os.PathLike, Path]

__all__ = [
    "find_repo_root",
    "build_dir",
    "ensure_dir",
    "resolve_build_path",
    "utc_ts",
    "log",
    "run_cmd",
    "persist_command_result",
    "write_json",
    "read_json",
]

def find_repo_root(start: Optional[Pathish] = None) -> Path:
    p = Path(start or Path.cwd()).resolve()
    candidates = ("pyproject.toml", "setup.cfg", "requirements.txt", ".git", "runtime")
    for cur in [p, *p.parents]:
        for name in candidates:
            if (cur / name).exists():
                return cur
    return p

def build_dir(start: Optional[Pathish] = None) -> Path:
    root = find_repo_root(start)
    d = root / "runtime" / "_build"
    d.mkdir(parents=True, exist_ok=True)
    return d

def ensure_dir(p: Pathish) -> Path:
    d = Path(p)
    d.mkdir(parents=True, exist_ok=True)
    return d

def resolve_build_path(*parts: str, start: Optional[Pathish] = None) -> Path:
    return build_dir(start).joinpath(*parts)

def utc_ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def log(msg: str, *, start: Optional[Pathish] = None, also_print: bool = True) -> None:
    line = f"[{utc_ts()}] {msg}"
    if also_print:
        print(line)
    try:
        lp = resolve_build_path("build.log", start=start)
        lp.parent.mkdir(parents=True, exist_ok=True)
        with lp.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def write_json(path: Pathish, obj: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

def read_json(path: Pathish, default: Any = None) -> Any:
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))

@dataclass
class CmdResult:
    cmd: List[str]
    cwd: str
    returncode: int
    duration_s: float
    stdout: str
    stderr: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cmd": self.cmd,
            "cwd": self.cwd,
            "returncode": self.returncode,
            "duration_s": self.duration_s,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }

def _as_cmd_list(cmd: Union[str, Sequence[str]]) -> List[str]:
    if isinstance(cmd, str):
        return [cmd]
    return [str(c) for c in cmd]

def run_cmd(
    cmd: Union[str, Sequence[str]],
    *,
    cwd: Optional[Pathish] = None,
    env: Optional[Mapping[str, str]] = None,
    timeout: Optional[float] = None,
    check: bool = False,
    start: Optional[Pathish] = None,
) -> CmdResult:
    cmd_list = _as_cmd_list(cmd)
    use_shell = isinstance(cmd, str)
    run_cwd = str(Path(cwd).resolve()) if cwd else str(Path.cwd().resolve())
    merged_env = os.environ.copy()
    if env:
        merged_env.update({str(k): str(v) for k, v in env.items()})
    log(f"RUN: {' '.join(cmd_list) if not use_shell else cmd_list[0]}", start=start, also_print=True)
    t0 = time.time()
    cp = subprocess.run(
        cmd if use_shell else cmd_list,
        cwd=run_cwd,
        env=merged_env,
        timeout=timeout,
        text=True,
        capture_output=True,
        shell=use_shell,
    )
    dur = time.time() - t0
    res = CmdResult(
        cmd=cmd_list if not use_shell else [cmd_list[0]],
        cwd=run_cwd,
        returncode=int(cp.returncode),
        duration_s=float(dur),
        stdout=cp.stdout or "",
        stderr=cp.stderr or "",
    )
    if check and res.returncode != 0:
        raise subprocess.CalledProcessError(res.returncode, cmd, output=res.stdout, stderr=res.stderr)
    log(f"EXIT {res.returncode} ({res.duration_s:.2f}s)", start=start, also_print=True)
    return res

def persist_command_result(
    name: str,
    result: CmdResult,
    *,
    start: Optional[Pathish] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    b = build_dir(start)
    raw_dir = ensure_dir(b / "raw")
    safe = "".join(c if (c.isalnum() or c in ("-", "_", ".")) else "_" for c in name).strip("_") or "command"
    meta = result.to_dict()
    if extra:
        meta.update(extra)
    meta["name"] = name
    meta["timestamp_utc"] = utc_ts()
    write_json(raw_dir / f"{safe}.json", meta)
    (raw_dir / f"{safe}.stdout.txt").write_text(result.stdout, encoding="utf-8")
    (raw_dir / f"{safe}.stderr.txt").write_text(result.stderr, encoding="utf-8")
    # Update simple rolling summary
    summary_path = b / "summary.json"
    summary = read_json(summary_path, default={"timestamp_utc": utc_ts(), "commands": []})
    summary["timestamp_utc"] = utc_ts()
    summary.setdefault("commands", [])
    summary["commands"].append({k: meta.get(k) for k in ("name", "timestamp_utc", "returncode", "duration_s", "cmd", "cwd")})
    write_json(summary_path, summary)
    return meta
