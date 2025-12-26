from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import platform
import subprocess
import sys
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S-%f")[:-3] + "Z"


def project_root(start: Optional[Path] = None) -> Path:
    p = (start or Path(__file__)).resolve()
    return p.parent.parent


def ensure_outputs_dirs(root: Optional[Path] = None) -> Tuple[Path, Path]:
    root = root or project_root()
    out = root / "outputs"
    logs = out / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    return out, logs


def default_run_stamp(extra: Optional[Dict] = None) -> Dict:
    stamp = {
        "run_id": utc_timestamp(),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "cwd": str(Path.cwd()),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
    }
    if extra:
        stamp.update(extra)
    return stamp


def write_run_stamp(outputs_dir: Path, stamp: Dict, filename: str = "run_stamp.json") -> Path:
    outputs_dir.mkdir(parents=True, exist_ok=True)
    p = outputs_dir / filename
    p.write_text(json.dumps(stamp, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return p


@dataclass(frozen=True)
class SubprocessResult:
    returncode: int
    cmd: List[str]
    log_path: Path


def run_and_capture_log(
    cmd: Sequence[str],
    log_path: Path,
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    timeout: Optional[float] = None,
) -> SubprocessResult:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    cmd_list = list(map(str, cmd))
    merged_env = os.environ.copy()
    if env:
        merged_env.update({str(k): str(v) for k, v in env.items()})
    with log_path.open("w", encoding="utf-8") as f:
        f.write(f"# cmd: {json.dumps(cmd_list)}\n")
        f.write(f"# cwd: {str(cwd) if cwd else str(Path.cwd())}\n")
        f.write(f"# started_utc: {datetime.now(timezone.utc).isoformat()}\n\n")
        f.flush()
        p = subprocess.Popen(
            cmd_list,
            cwd=str(cwd) if cwd else None,
            env=merged_env,
            stdout=f,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            rc = p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            p.kill()
            rc = p.wait()
            f.write(f"\n# timeout_expired: {timeout}\n")
        f.write(f"\n# finished_utc: {datetime.now(timezone.utc).isoformat()}\n")
        f.write(f"# returncode: {rc}\n")
    return SubprocessResult(returncode=rc, cmd=cmd_list, log_path=log_path)


def _iter_files(root: Path) -> Iterable[Path]:
    for p in sorted(root.rglob("*")):
        if p.is_file():
            yield p


def discover_outputs(outputs_dir: Path) -> Dict[str, List[str]]:
    outputs_dir = outputs_dir.resolve()
    logs_dir = outputs_dir / "logs"
    logs: List[str] = []
    artifacts: List[str] = []
    for p in _iter_files(outputs_dir):
        rel = p.relative_to(outputs_dir).as_posix()
        if rel == "index.md":
            continue
        if p.is_relative_to(logs_dir):
            logs.append(rel)
        else:
            artifacts.append(rel)
    logs.sort(reverse=True)
    artifacts.sort()
    return {"logs": logs, "artifacts": artifacts}


def update_outputs_index(outputs_dir: Path, title: str = "Outputs Index") -> Path:
    outputs_dir.mkdir(parents=True, exist_ok=True)
    idx = outputs_dir / "index.md"
    d = discover_outputs(outputs_dir)
    lines: List[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"_Generated: {datetime.now(timezone.utc).isoformat()}_")
    lines.append("")
    lines.append("## Logs")
    lines.append("")
    if d["logs"]:
        for rel in d["logs"]:
            lines.append(f"- [{rel}](./{rel})")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    if d["artifacts"]:
        for rel in d["artifacts"]:
            lines.append(f"- [{rel}](./{rel})")
    else:
        lines.append("- (none)")
    lines.append("")
    idx.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return idx
