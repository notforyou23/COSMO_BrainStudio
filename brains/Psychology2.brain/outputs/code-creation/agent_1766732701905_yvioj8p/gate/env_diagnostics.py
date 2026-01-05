from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _now_iso() -> str:
    try:
        return time.strftime("%Y-%m-%dT%H:%M:%S%z")
    except Exception:
        return ""


def _read_text(path: Path, limit: int = 4000) -> str:
    try:
        data = path.read_text(errors="replace")
        return data[:limit]
    except Exception:
        return ""


def _run(cmd: List[str], timeout: float = 3.0) -> Dict[str, Any]:
    out: Dict[str, Any] = {"cmd": cmd, "ok": False, "rc": None, "stdout": "", "stderr": "", "timeout_s": timeout}
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        out.update(ok=(p.returncode == 0), rc=p.returncode, stdout=(p.stdout or "").strip(), stderr=(p.stderr or "").strip())
    except FileNotFoundError:
        out.update(ok=False, rc=None, stderr="not_found")
    except subprocess.TimeoutExpired as e:
        out.update(ok=False, rc=None, stdout=(getattr(e, "stdout", "") or "").strip(), stderr="timeout")
    except Exception as e:
        out.update(ok=False, rc=None, stderr=f"{type(e).__name__}: {e}")
    return out


def _which(exe: str) -> Optional[str]:
    try:
        return shutil.which(exe)
    except Exception:
        return None


def _is_probably_container() -> bool:
    try:
        if Path("/.dockerenv").exists():
            return True
        cgroup = _read_text(Path("/proc/1/cgroup"), 4000)
        if any(x in cgroup for x in ("docker", "kubepods", "containerd", "podman")):
            return True
    except Exception:
        pass
    return False


def _fs_entry(path: Path) -> Dict[str, Any]:
    info: Dict[str, Any] = {"path": str(path)}
    try:
        info["exists"] = path.exists()
        info["is_file"] = path.is_file()
        info["is_dir"] = path.is_dir()
        try:
            info["resolved"] = str(path.resolve())
        except Exception:
            info["resolved"] = str(path)
        if path.exists():
            st = path.stat()
            info["mode"] = oct(st.st_mode & 0o7777)
            info["size"] = int(getattr(st, "st_size", 0))
            info["mtime"] = float(getattr(st, "st_mtime", 0.0))
    except Exception as e:
        info["error"] = f"{type(e).__name__}: {e}"
    return info


def _disk_usage(path: Path) -> Dict[str, Any]:
    out: Dict[str, Any] = {"path": str(path)}
    try:
        du = shutil.disk_usage(str(path))
        out.update(total=int(du.total), used=int(du.used), free=int(du.free))
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
    return out


def _env_subset(keys: Iterable[str]) -> Dict[str, str]:
    env = os.environ
    out: Dict[str, str] = {}
    for k in keys:
        v = env.get(k)
        if v is not None:
            out[k] = v
    return out


def gather(project_root: Optional[Path] = None, extra_paths: Optional[Iterable[Path]] = None) -> Dict[str, Any]:
    pr = Path(project_root) if project_root else Path.cwd()
    paths = [pr, pr / "gate", pr / "runtime", pr / "runtime/_build"]
    if extra_paths:
        paths.extend([Path(p) for p in extra_paths])
    paths = [p for i, p in enumerate(paths) if str(p) and str(p) not in {str(x) for x in paths[:i]}]

    whoami = _run(["id"], timeout=2.0) if platform.system().lower() != "windows" else {"ok": False, "stderr": "unsupported"}
    docker_path = _which("docker")
    docker_version = _run(["docker", "version", "--format", "{{json .}}"], timeout=4.0) if docker_path else {"ok": False, "stderr": "docker_not_in_path"}
    docker_info = _run(["docker", "info", "--format", "{{json .}}"], timeout=4.0) if docker_path else {"ok": False, "stderr": "docker_not_in_path"}

    data: Dict[str, Any] = {
        "timestamp": _now_iso(),
        "cwd": str(Path.cwd()),
        "project_root": str(pr),
        "python": {
            "executable": sys.executable,
            "version": sys.version.replace("\n", " "),
            "prefix": sys.prefix,
            "base_prefix": getattr(sys, "base_prefix", ""),
            "path": sys.path[:],
        },
        "os": {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "hostname": socket.gethostname(),
            "in_container": _is_probably_container(),
        },
        "env": _env_subset(
            [
                "PATH",
                "PYTHONPATH",
                "VIRTUAL_ENV",
                "CONDA_PREFIX",
                "CONDA_DEFAULT_ENV",
                "HOME",
                "SHELL",
                "USER",
                "LOGNAME",
                "PWD",
                "CI",
                "GITHUB_ACTIONS",
                "RUNNER_OS",
                "DOCKER_HOST",
                "DOCKER_CONTEXT",
            ]
        ),
        "executables": {"docker": docker_path, "python": _which("python"), "python3": _which("python3")},
        "id": whoami,
        "docker": {"version": docker_version, "info": docker_info},
        "filesystem": {"paths": [_fs_entry(p) for p in paths], "disk_usage": [_disk_usage(pr)]},
    }

    try:
        data["limits"] = {"open_files": _run(["bash", "-lc", "ulimit -n"], timeout=2.0)}
    except Exception:
        data["limits"] = {}
    return data


def format_text(diag: Dict[str, Any]) -> str:
    lines: List[str] = []
    def add(k: str, v: Any) -> None:
        lines.append(f"{k}: {v}")

    add("timestamp", diag.get("timestamp", ""))
    add("cwd", diag.get("cwd", ""))
    add("project_root", diag.get("project_root", ""))
    osd = diag.get("os", {}) or {}
    add("os.platform", osd.get("platform", ""))
    add("os.in_container", osd.get("in_container", ""))
    py = diag.get("python", {}) or {}
    add("python.executable", py.get("executable", ""))
    add("python.version", py.get("version", ""))

    env = diag.get("env", {}) or {}
    for k in ("PATH", "PYTHONPATH", "VIRTUAL_ENV", "CONDA_PREFIX", "CI", "DOCKER_HOST", "DOCKER_CONTEXT"):
        if k in env:
            add(f"env.{k}", env.get(k, ""))

    exe = diag.get("executables", {}) or {}
    add("docker.which", exe.get("docker", None))
    dv = ((diag.get("docker", {}) or {}).get("version", {}) or {})
    add("docker.version.ok", dv.get("ok", False))
    if dv.get("stderr"):
        add("docker.version.stderr", dv.get("stderr"))
    if dv.get("stdout"):
        s = dv.get("stdout", "")
        add("docker.version.stdout_head", s[:300])

    fs = (diag.get("filesystem", {}) or {}).get("paths", []) or []
    for p in fs:
        add(f"fs.{p.get('path')}.exists", p.get("exists"))
        if p.get("error"):
            add(f"fs.{p.get('path')}.error", p.get("error"))

    return "\n".join(lines).rstrip() + "\n"


def to_json(diag: Dict[str, Any]) -> str:
    return json.dumps(diag, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
