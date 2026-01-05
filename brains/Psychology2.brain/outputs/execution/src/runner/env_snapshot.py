"""Environment snapshot collector.

Writes a stable, reproducible JSON snapshot of host + Docker + relevant env data.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import datetime as _dt
import getpass
import json
import os
import platform
import socket
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple
def _run(cmd: List[str], timeout_s: float = 3.0) -> Tuple[int, str, str]:
    try:
        p = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        return int(p.returncode), (p.stdout or "").strip(), (p.stderr or "").strip()
    except FileNotFoundError as e:
        return 127, "", f"{type(e).__name__}: {e}"
    except Exception as e:
        return 1, "", f"{type(e).__name__}: {e}"


def _read_text(path: str, max_bytes: int = 65536) -> Optional[str]:
    try:
        with open(path, "rb") as f:
            data = f.read(max_bytes)
        return data.decode("utf-8", errors="replace").strip()
    except Exception:
        return None
def _collect_os_release() -> Dict[str, Any]:
    txt = _read_text("/etc/os-release")
    if not txt:
        return {}
    out: Dict[str, Any] = {}
    for line in txt.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"')
        out[k.strip()] = v
    return out


def _collect_env() -> Dict[str, str]:
    allow_exact = {
        "CI",
        "GITHUB_ACTIONS",
        "GITLAB_CI",
        "BUILDKITE",
        "JENKINS_URL",
        "TEAMCITY_VERSION",
        "DOCKER_HOST",
        "DOCKER_CONTEXT",
        "DOCKER_BUILDKIT",
        "DOCKER_CONFIG",
        "KUBECONFIG",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
    }
    allow_prefixes = ("GITHUB_", "GITLAB_", "BUILDKITE_", "CI_", "DOCKER_")
    out: Dict[str, str] = {}
    for k in sorted(os.environ.keys()):
        if k in allow_exact or k.startswith(allow_prefixes):
            out[k] = os.environ.get(k, "")
    return out


def _collect_python() -> Dict[str, Any]:
    return {
        "executable": sys.executable,
        "version": sys.version.replace("\n", " "),
        "version_info": list(sys.version_info[:]),
        "implementation": platform.python_implementation(),
        "prefix": sys.prefix,
        "base_prefix": getattr(sys, "base_prefix", None),
        "path": list(sys.path),
    }
def _collect_docker() -> Dict[str, Any]:
    docker: Dict[str, Any] = {"available": False}
    rc, out, err = _run(["docker", "version", "--format", "{{json .}}"], timeout_s=6.0)
    docker["version_rc"] = rc
    if out:
        try:
            docker["version"] = json.loads(out)
            docker["available"] = True
        except Exception:
            docker["version_raw"] = out
    if err:
        docker["version_err"] = err

    rc2, out2, err2 = _run(["docker", "info", "--format", "{{json .}}"], timeout_s=6.0)
    docker["info_rc"] = rc2
    if out2:
        try:
            docker["info"] = json.loads(out2)
            docker["available"] = docker.get("available", False) or True
        except Exception:
            docker["info_raw"] = out2
    if err2:
        docker["info_err"] = err2

    # Normalize potentially non-deterministic maps into sorted (key, value) lists where helpful.
    info = docker.get("info")
    if isinstance(info, dict):
        for k in ("Labels", "RegistryConfig", "Plugins", "Runtimes"):
            v = info.get(k)
            if isinstance(v, dict):
                info[k] = [[kk, v[kk]] for kk in sorted(v.keys())]
        # Some fields may be huge; keep them but ensure stable key ordering on serialization.
        docker["info"] = info

    return docker


def _collect_host() -> Dict[str, Any]:
    uid = getattr(os, "getuid", lambda: None)()
    gid = getattr(os, "getgid", lambda: None)()
    uname = platform.uname()
    rc, uname_s, _ = _run(["uname", "-a"], timeout_s=2.0)
    return {
        "hostname": socket.gethostname(),
        "fqdn": socket.getfqdn(),
        "user": getpass.getuser(),
        "uid": uid,
        "gid": gid,
        "cwd": os.getcwd(),
        "platform": {
            "system": uname.system,
            "node": uname.node,
            "release": uname.release,
            "version": uname.version,
            "machine": uname.machine,
            "processor": uname.processor,
            "python_platform": platform.platform(),
            "uname_a": uname_s if rc == 0 else None,
        },
        "os_release": _collect_os_release(),
    }
def collect_env_snapshot() -> Dict[str, Any]:
    # Formatting is deterministic (sorted keys, stable lists), but snapshot content reflects current environment.
    return {
        "schema_version": 1,
        "collected_at_utc": _dt.datetime.now(tz=_dt.timezone.utc).isoformat(),
        "host": _collect_host(),
        "python": _collect_python(),
        "docker": _collect_docker(),
        "env": _collect_env(),
    }


def write_env_snapshot(path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    snap = collect_env_snapshot()
    tmp = path.with_suffix(path.suffix + ".tmp")
    data = json.dumps(snap, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    tmp.write_text(data, encoding="utf-8")
    tmp.replace(path)
    return path
