#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
from pathlib import Path

try:
    from importlib import metadata as _ilmd
except Exception:  # pragma: no cover
    _ilmd = None


def _now_utc_stamp() -> str:
    return _dt.datetime.utcnow().strftime('%Y-%m-%dT%H-%M-%S-%fZ')


def _read_text(path: str) -> str | None:
    try:
        p = Path(path)
        return p.read_text(encoding='utf-8', errors='replace')
    except Exception:
        return None


def _run(cmd: list[str], timeout: int = 8) -> dict:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return {"cmd": cmd, "returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
    except Exception as e:
        return {"cmd": cmd, "error": repr(e)}


def _get_cgroup_limits() -> dict:
    out: dict = {}
    # cgroup v2
    mem_max = _read_text("/sys/fs/cgroup/memory.max")
    cpu_max = _read_text("/sys/fs/cgroup/cpu.max")
    if mem_max is not None:
        out["memory.max"] = mem_max.strip()
    if cpu_max is not None:
        out["cpu.max"] = cpu_max.strip()
    # common v1 locations (best-effort)
    for p in ["/sys/fs/cgroup/memory/memory.limit_in_bytes", "/sys/fs/cgroup/cpu/cpu.cfs_quota_us"]:
        t = _read_text(p)
        if t is not None:
            out[Path(p).name] = t.strip()
    cg = _read_text("/proc/self/cgroup")
    if cg is not None:
        out["/proc/self/cgroup"] = cg.strip().splitlines()[:200]
    return out


def _get_resources() -> dict:
    res: dict = {"cpu_count": os.cpu_count()}
    meminfo = _read_text("/proc/meminfo")
    if meminfo:
        for line in meminfo.splitlines():
            if line.startswith("MemTotal:") or line.startswith("MemAvailable:"):
                k, v = line.split(":", 1)
                res.setdefault("meminfo_kb", {})[k.strip()] = v.strip()
    try:
        du = shutil.disk_usage(str(Path.cwd()))
        res["disk_usage_cwd_bytes"] = {"total": du.total, "used": du.used, "free": du.free}
    except Exception as e:
        res["disk_usage_cwd_bytes_error"] = repr(e)
    res["cgroup"] = _get_cgroup_limits()
    return res


def _get_container_identity() -> dict:
    ident: dict = {
        "hostname": socket.gethostname(),
        "container_id_guess": os.environ.get("HOSTNAME") or socket.gethostname(),
    }
    for k in ["CONTAINER_IMAGE", "IMAGE_ID", "IMAGE_SHA", "DOCKER_IMAGE", "KUBERNETES_SERVICE_HOST"]:
        if os.environ.get(k):
            ident.setdefault("env_hints", {})[k] = os.environ.get(k)
    # heuristic: some runtimes provide image digest in /proc/1/cpuset or mounts; record minimal hints
    ident["/proc/1/cgroup_head"] = (_read_text("/proc/1/cgroup") or "").splitlines()[:50]
    # if docker cli exists, attempt to inspect this container id (may fail without socket access)
    if shutil.which("docker"):
        ident["docker_version"] = _run(["docker", "version", "--format", "{{json .}}"], timeout=10)
        cid = ident.get("container_id_guess") or ""
        if cid:
            ident["docker_inspect_self"] = _run(["docker", "inspect", cid], timeout=10)
    return ident


def _get_os_details() -> dict:
    return {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": {
            "executable": sys.executable,
            "version": sys.version,
            "implementation": platform.python_implementation(),
        },
        "uname": getattr(platform, "uname")()._asdict() if hasattr(platform, "uname") else None,
        "os_release": _read_text("/etc/os-release"),
    }


def _get_dependency_versions(limit: int | None = None) -> dict:
    deps: dict = {}
    if _ilmd is None:
        return {"error": "importlib.metadata unavailable"}
    try:
        dists = []
        for d in _ilmd.distributions():
            try:
                name = d.metadata.get("Name") or d.metadata.get("Summary") or d.name
            except Exception:
                name = getattr(d, "name", "unknown")
            ver = getattr(d, "version", None)
            dists.append((str(name), str(ver) if ver is not None else None))
        dists.sort(key=lambda x: (x[0] or "").lower())
        if limit is not None:
            dists = dists[: max(0, int(limit))]
        deps["distributions"] = [{"name": n, "version": v} for n, v in dists]
        deps["count"] = len(dists)
    except Exception as e:
        deps["error"] = repr(e)
    # quick checks for common tooling
    for tool in ["python", "pip", "git", "docker"]:
        if shutil.which(tool):
            deps.setdefault("tool_versions", {})[tool] = _run([tool, "--version"], timeout=8)
    return deps


def write_env_dump(out_dir: Path, tag: str = "env_dump", limit_deps: int | None = None) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = _now_utc_stamp()
    path = out_dir / f"{stamp}_{tag}.json"
    payload = {
        "timestamp_utc": stamp,
        "cwd": str(Path.cwd()),
        "pid": os.getpid(),
        "ppid": os.getppid(),
        "uid": getattr(os, "getuid", lambda: None)(),
        "gid": getattr(os, "getgid", lambda: None)(),
        "env_subset": {k: os.environ.get(k) for k in sorted(set([
            "CI", "GITHUB_ACTIONS", "GITLAB_CI", "BUILDKITE", "JENKINS_URL",
            "KUBERNETES_SERVICE_HOST", "HOSTNAME", "USER", "HOME", "PATH",
            "PYTHONPATH", "VIRTUAL_ENV", "CONDA_PREFIX"
        ])) if os.environ.get(k) is not None},
        "os": _get_os_details(),
        "resources": _get_resources(),
        "container": _get_container_identity(),
        "dependencies": _get_dependency_versions(limit=limit_deps),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    # best-effort canonical latest pointer (as file copy)
    try:
        latest = out_dir / f"{tag}_latest.json"
        latest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception:
        pass
    return path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Write a structured environment dump for failure triage.")
    ap.add_argument("--out-dir", default="outputs/qa/exec_logs", help="Output directory (relative or absolute).")
    ap.add_argument("--tag", default="env_dump", help="Tag used in output filename.")
    ap.add_argument("--limit-deps", type=int, default=None, help="Limit number of distributions recorded.")
    args = ap.parse_args(argv)
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = Path.cwd() / out_dir
    p = write_env_dump(out_dir=out_dir, tag=args.tag, limit_deps=args.limit_deps)
    sys.stdout.write(str(p) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
