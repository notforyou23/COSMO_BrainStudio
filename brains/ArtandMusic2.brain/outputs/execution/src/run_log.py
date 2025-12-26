from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple, Union
import datetime as _dt
import json
import os
import platform
import subprocess
import sys
def _utc_now_iso() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _json_default(obj: Any) -> str:
    try:
        return str(obj)
    except Exception:
        return repr(obj)


def _run_cmd(cmd: Iterable[str], cwd: Optional[Union[str, Path]] = None, timeout: float = 2.0) -> Tuple[int, str]:
    try:
        p = subprocess.run(
            list(cmd),
            cwd=str(cwd) if cwd is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
        return int(p.returncode), (p.stdout or "").strip()
    except Exception as e:
        return 1, f"{type(e).__name__}: {e}
def collect_environment(project_root: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    root = Path(project_root).resolve() if project_root else None
    env: Dict[str, Any] = {
        "timestamp_utc": _utc_now_iso(),
        "python": {
            "version": sys.version.splitlines()[0],
            "executable": sys.executable,
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
        },
        "process": {
            "pid": os.getpid(),
            "cwd": str(Path.cwd().resolve()),
            "argv": list(sys.argv),
        },
        "project_root": str(root) if root else None,
    }

    if root:
        code, out = _run_cmd(["git", "rev-parse", "HEAD"], cwd=root)
        if code == 0 and out:
            env["git"] = {"head": out}
            code2, out2 = _run_cmd(["git", "status", "--porcelain"], cwd=root)
            if code2 == 0:
                env["git"]["dirty"] = bool(out2.strip())
        else:
            env["git"] = {"error": out or "not a git repo / git unavailable"}
    return env
def format_text_log(event: Dict[str, Any]) -> str:
    ts = event.get("timestamp_utc") or _utc_now_iso()
    lines = [f"Run Log - {ts}"]
    lines.append("")
    env = event.get("environment") or {}
    pr = env.get("process") or {}
    py = env.get("python") or {}
    plat = env.get("platform") or {}
    lines.append("Environment")
    lines.append(f"  cwd: {pr.get('cwd')}")
    lines.append(f"  argv: {pr.get('argv')}")
    lines.append(f"  python: {py.get('version')} ({py.get('executable')})")
    lines.append(f"  platform: {plat.get('system')} {plat.get('release')} ({plat.get('machine')})")
    if env.get("project_root"):
        lines.append(f"  project_root: {env.get('project_root')}")
    git = env.get("git")
    if isinstance(git, dict):
        if git.get("head"):
            lines.append(f"  git_head: {git.get('head')}")
            lines.append(f"  git_dirty: {git.get('dirty')}")
        elif git.get("error"):
            lines.append(f"  git: {git.get('error')}")
    lines.append("")
    lines.append("Verification")
    ver = event.get("verification") or {}
    ok = ver.get("ok")
    if ok is not None:
        lines.append(f"  ok: {bool(ok)}")
    missing = ver.get("missing") or []
    extra = ver.get("extra") or []
    if missing:
        lines.append("  missing:")
        for p in missing:
            lines.append(f"    - {p}")
    if extra:
        lines.append("  extra:")
        for p in extra:
            lines.append(f"    - {p}")
    details = ver.get("details")
    if details:
        try:
            txt = json.dumps(details, indent=2, ensure_ascii=False, default=_json_default)
        except Exception:
            txt = str(details)
        lines.append("")
        lines.append("Details")
        lines.append(txt)
    return "\n".join(lines).rstrip() + "\n"
@dataclass(frozen=True)
class RunLogPaths:
    jsonl: Optional[Path]
    text: Optional[Path]


def write_run_log(
    logs_dir: Union[str, Path],
    *,
    environment: Optional[Dict[str, Any]] = None,
    verification: Optional[Dict[str, Any]] = None,
    event_type: str = "init_outputs",
    prefix: str = "run",
    write_jsonl: bool = True,
    write_text: bool = True,
    project_root: Optional[Union[str, Path]] = None,
) -> RunLogPaths:
    logs = Path(logs_dir).resolve()
    logs.mkdir(parents=True, exist_ok=True)

    ts = _utc_now_iso().replace(":", "").replace("-", "")
    stem = f"{prefix}_{ts}"

    env = environment if environment is not None else collect_environment(project_root=project_root)
    event: Dict[str, Any] = {
        "timestamp_utc": env.get("timestamp_utc") or _utc_now_iso(),
        "type": event_type,
        "environment": env,
        "verification": verification or {},
    }

    jsonl_path = logs / f"{stem}.jsonl" if write_jsonl else None
    text_path = logs / f"{stem}.log" if write_text else None

    if jsonl_path:
        line = json.dumps(event, ensure_ascii=False, default=_json_default)
        with jsonl_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    if text_path:
        text = format_text_log(event)
        text_path.write_text(text, encoding="utf-8")

    return RunLogPaths(jsonl=jsonl_path, text=text_path)
