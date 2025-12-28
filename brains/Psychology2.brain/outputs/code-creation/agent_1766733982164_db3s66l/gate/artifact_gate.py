#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import json
import time
import shutil
import socket
import platform
import subprocess
from pathlib import Path


def _run(cmd, timeout=12, env=None):
    p = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        env=env,
    )
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def _short(s, n=500):
    s = "" if s is None else str(s)
    return s if len(s) <= n else (s[:n] + "…")


def _fs_probe(path: Path):
    info = {"path": str(path), "exists": path.exists()}
    try:
        info["resolved"] = str(path.resolve())
    except Exception as e:
        info["resolved_error"] = f"{type(e).__name__}: {e}"
    if info["exists"]:
        try:
            info["is_dir"] = path.is_dir()
            info["is_file"] = path.is_file()
            info["is_symlink"] = path.is_symlink()
        except Exception as e:
            info["stat_error"] = f"{type(e).__name__}: {e}"
    try:
        info["readable"] = os.access(path, os.R_OK)
        info["writable"] = os.access(path, os.W_OK)
        info["executable"] = os.access(path, os.X_OK)
    except Exception as e:
        info["access_error"] = f"{type(e).__name__}: {e}"
    return info


def _disk_probe(path: Path):
    try:
        st = shutil.disk_usage(str(path))
        return {"total": st.total, "used": st.used, "free": st.free}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def env_diagnostics():
    here = Path(__file__).resolve()
    gate_dir = here.parent
    project_root = gate_dir.parent
    cwd = Path.cwd()
    diag = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python": {
            "executable": sys.executable,
            "version": sys.version.splitlines()[0],
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "process": {
            "pid": os.getpid(),
            "ppid": os.getppid(),
            "uid": getattr(os, "getuid", lambda: None)(),
            "gid": getattr(os, "getgid", lambda: None)(),
        },
        "paths": {
            "cwd": str(cwd),
            "script": str(here),
            "gate_dir": str(gate_dir),
            "project_root_guess": str(project_root),
            "PATH": _short(os.environ.get("PATH", "")),
            "PYTHONPATH": _short(os.environ.get("PYTHONPATH", "")),
        },
        "fs": {
            "cwd": _fs_probe(cwd),
            "gate_dir": _fs_probe(gate_dir),
            "project_root_guess": _fs_probe(project_root),
            "disk": {
                "cwd": _disk_probe(cwd),
                "project_root_guess": _disk_probe(project_root),
            },
        },
    }
    expected = [
        project_root / "gate",
        project_root / "runtime",
        project_root / "runtime" / "_build",
        project_root / "runtime" / "_build" / "reports",
    ]
    diag["fs"]["expected_paths"] = [_fs_probe(p) for p in expected]
    return diag


def docker_healthcheck():
    res = {
        "docker_on_path": False,
        "docker_path": None,
        "sock_exists": None,
        "sock_access_rw": None,
        "version_rc": None,
        "version_out": None,
        "version_err": None,
        "info_rc": None,
        "info_err": None,
    }
    dp = shutil.which("docker")
    res["docker_on_path"] = bool(dp)
    res["docker_path"] = dp
    sock = Path("/var/run/docker.sock")
    res["sock_exists"] = sock.exists()
    try:
        res["sock_access_rw"] = os.access(sock, os.R_OK | os.W_OK)
    except Exception:
        res["sock_access_rw"] = None

    if not dp:
        return res

    env = dict(os.environ)
    env.setdefault("DOCKER_CLI_HINTS", "false")
    try:
        rc, out, err = _run(["docker", "version"], timeout=12, env=env)
        res["version_rc"], res["version_out"], res["version_err"] = rc, _short(out, 1200), _short(err, 1200)
    except subprocess.TimeoutExpired:
        res["version_rc"], res["version_err"] = -1, "timeout"
    except Exception as e:
        res["version_rc"], res["version_err"] = -2, f"{type(e).__name__}: {e}"

    try:
        rc, out, err = _run(["docker", "info"], timeout=12, env=env)
        res["info_rc"], res["info_err"] = rc, _short(err or out, 1200)
    except subprocess.TimeoutExpired:
        res["info_rc"], res["info_err"] = -1, "timeout"
    except Exception as e:
        res["info_rc"], res["info_err"] = -2, f"{type(e).__name__}: {e}"

    return res


def _can_resolve_dns(host="registry-1.docker.io", timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.getaddrinfo(host, 443)
        return True, None
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def preflight(require_docker=True):
    diag = env_diagnostics()
    diag["docker"] = docker_healthcheck()
    ok_dns, dns_err = _can_resolve_dns()
    diag["network"] = {"dns_registry_ok": ok_dns, "dns_registry_error": dns_err}

    issues = []
    d = diag["docker"]
    if require_docker:
        if not d["docker_on_path"]:
            issues.append("docker_not_on_PATH")
        elif d.get("version_rc") not in (0, None):
            issues.append("docker_unusable_or_daemon_unreachable")
    if diag["fs"]["cwd"].get("writable") is False:
        issues.append("cwd_not_writable")
    if diag["fs"]["project_root_guess"].get("exists") is False:
        issues.append("project_root_missing_or_unmounted")
    diag["issues"] = issues
    return diag, (len(issues) == 0)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    require_docker = ("--no-docker" not in argv)
    as_json = ("--json" in argv)
    diagnose_only = ("--diagnose" in argv)

    diag, ok = preflight(require_docker=require_docker)

    if as_json:
        print(json.dumps(diag, indent=2, sort_keys=True))
    else:
        print("artifact_gate: preflight diagnostics")
        print("cwd:", diag["paths"]["cwd"])
        print("script:", diag["paths"]["script"])
        print("docker:", "ok" if diag["docker"].get("version_rc") == 0 else "not_ok")
        if diag.get("issues"):
            print("issues:", ", ".join(diag["issues"]))

    if diagnose_only:
        return 0 if ok else 2

    if not ok:
        if not as_json:
            print("artifact_gate: failing fast to avoid container-loss (run with --json --diagnose for full details).", file=sys.stderr)
        return 2

    # If integrated into a larger pipeline, this script can serve as an early gate.
    if not as_json:
        print("artifact_gate: preflight passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
