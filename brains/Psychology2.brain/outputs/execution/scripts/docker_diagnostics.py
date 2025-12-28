from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
import os
import subprocess
import time
from typing import Iterable, Optional, Sequence, Union, Dict, Any, List

PathLike = Union[str, Path]

def utc_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def ensure_dir(p: PathLike) -> Path:
    p = Path(p)
    p.mkdir(parents=True, exist_ok=True)
    return p

def _coerce_args(args: Union[str, Sequence[str]]) -> List[str]:
    if isinstance(args, str):
        return [args]
    return list(args)

@dataclass
class CmdResult:
    argv: List[str]
    returncode: int
    started_utc: str
    duration_s: float
    stdout: str
    stderr: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "argv": self.argv,
            "returncode": self.returncode,
            "started_utc": self.started_utc,
            "duration_s": self.duration_s,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }

def run_cmd(args: Union[str, Sequence[str]], timeout_s: int = 60, env: Optional[Dict[str, str]] = None) -> CmdResult:
    argv = _coerce_args(args)
    started = utc_ts()
    t0 = time.time()
    try:
        p = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env={**os.environ, **(env or {})},
        )
        rc, out, err = p.returncode, p.stdout or "", p.stderr or ""
    except subprocess.TimeoutExpired as e:
        rc = 124
        out = (e.stdout or "") if isinstance(e.stdout, str) else ""
        err = (e.stderr or "") if isinstance(e.stderr, str) else ""
        err = (err + "\n" if err else "") + f"TIMEOUT after {timeout_s}s"
    return CmdResult(argv=argv, returncode=rc, started_utc=started, duration_s=round(time.time() - t0, 3), stdout=out, stderr=err)

def write_artifact(out_dir: PathLike, name: str, content: str) -> Path:
    out_dir = ensure_dir(out_dir)
    p = out_dir / name
    p.write_text(content, encoding="utf-8")
    return p

def write_cmd_artifacts(out_dir: PathLike, stem: str, res: CmdResult) -> None:
    out_dir = ensure_dir(out_dir)
    meta = [
        f"started_utc: {res.started_utc}",
        f"duration_s: {res.duration_s}",
        f"returncode: {res.returncode}",
        f"argv: {' '.join(res.argv)}",
        "",
    ]
    write_artifact(out_dir, f"{stem}.stdout.txt", res.stdout)
    write_artifact(out_dir, f"{stem}.stderr.txt", "\n".join(meta) + res.stderr)

def docker_available() -> bool:
    res = run_cmd(["docker", "version"], timeout_s=15)
    return res.returncode == 0

def capture_docker_basics(out_dir: PathLike, prefix: str = "docker") -> Dict[str, CmdResult]:
    out_dir = ensure_dir(out_dir)
    ts = utc_ts()
    cmds = {
        "version": ["docker", "version"],
        "info": ["docker", "info"],
        "ps": ["docker", "ps", "-a", "--no-trunc"],
        "images": ["docker", "images", "--no-trunc"],
        "networks": ["docker", "network", "ls"],
        "volumes": ["docker", "volume", "ls"],
    }
    results: Dict[str, CmdResult] = {}
    for k, argv in cmds.items():
        res = run_cmd(argv, timeout_s=60)
        results[k] = res
        write_cmd_artifacts(out_dir, f"{prefix}_{k}_{ts}", res)
    return results

def inspect_containers(container_ids: Iterable[str], out_dir: PathLike, prefix: str = "docker_inspect") -> Dict[str, CmdResult]:
    out_dir = ensure_dir(out_dir)
    ts = utc_ts()
    results: Dict[str, CmdResult] = {}
    for cid in [c for c in container_ids if c]:
        safe = "".join(ch for ch in cid if ch.isalnum() or ch in "-_.")[:64] or "container"
        res = run_cmd(["docker", "inspect", cid], timeout_s=60)
        results[cid] = res
        write_cmd_artifacts(out_dir, f"{prefix}_{safe}_{ts}", res)
    return results

def capture_container_logs(container_id: str, out_dir: PathLike, tail: Optional[int] = 5000, since: Optional[str] = None,
                          prefix: str = "docker_logs") -> CmdResult:
    out_dir = ensure_dir(out_dir)
    ts = utc_ts()
    argv = ["docker", "logs", "--timestamps"]
    if since:
        argv += ["--since", since]
    if tail is not None:
        argv += ["--tail", str(int(tail))]
    argv.append(container_id)
    res = run_cmd(argv, timeout_s=60)
    safe = "".join(ch for ch in container_id if ch.isalnum() or ch in "-_.")[:64] or "container"
    write_cmd_artifacts(out_dir, f"{prefix}_{safe}_{ts}", res)
    return res

def sample_container_stats(container_ids: Iterable[str], out_dir: PathLike, samples: int = 5, interval_s: float = 1.0,
                           prefix: str = "docker_stats") -> List[CmdResult]:
    out_dir = ensure_dir(out_dir)
    ts = utc_ts()
    cids = [c for c in container_ids if c]
    if not cids:
        return []
    fmt = "{{.Container}}\t{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}\t{{.PIDs}}"
    results: List[CmdResult] = []
    for i in range(max(1, int(samples))):
        res = run_cmd(["docker", "stats", "--no-stream", "--no-trunc", "--format", fmt, *cids], timeout_s=30)
        results.append(res)
        write_cmd_artifacts(out_dir, f"{prefix}_{ts}_{i:03d}", res)
        if i + 1 < samples:
            time.sleep(max(0.0, float(interval_s)))
    return results
