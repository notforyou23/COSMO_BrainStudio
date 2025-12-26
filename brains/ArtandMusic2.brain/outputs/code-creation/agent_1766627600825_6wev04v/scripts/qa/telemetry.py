from __future__ import annotations
import os, sys, json, time, platform, socket, shutil, subprocess
from pathlib import Path

SENSITIVE = ("PASS", "PASSWORD", "SECRET", "TOKEN", "KEY", "CREDENTIAL", "AUTH", "COOKIE")

def _now():
    return time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime())

def _read_text(p: Path, limit: int = 200_000) -> str:
    try:
        b = p.read_bytes()
        if len(b) > limit: b = b[:limit] + b"\n...[truncated]..."
        return b.decode("utf-8", "replace")
    except Exception as e:
        return f"<unavailable:{type(e).__name__}:{e}>"

def _run(cmd, timeout=5):
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        return {"cmd": cmd, "returncode": p.returncode, "stdout": p.stdout[-200_000:], "stderr": p.stderr[-200_000:]}
    except Exception as e:
        return {"cmd": cmd, "error": f"{type(e).__name__}:{e}"}

def _env_redacted():
    out = {}
    for k, v in os.environ.items():
        if any(s in k.upper() for s in SENSITIVE): out[k] = "<redacted>"
        else: out[k] = v if len(v) <= 4000 else v[:4000] + "...[truncated]"
    return dict(sorted(out.items()))

def _rlimits():
    try:
        import resource
        names = [n for n in dir(resource) if n.startswith("RLIMIT_")]
        res = {}
        for n in sorted(names):
            try:
                cur, mx = resource.getrlimit(getattr(resource, n))
                res[n] = {"cur": cur, "max": mx}
            except Exception as e:
                res[n] = f"<unavailable:{type(e).__name__}:{e}>"
        return res
    except Exception as e:
        return {"error": f"{type(e).__name__}:{e}"}

def _disk(paths):
    d = {}
    for label, p in paths.items():
        try:
            u = shutil.disk_usage(str(p))
            d[label] = {"path": str(p), "total": u.total, "used": u.used, "free": u.free}
        except Exception as e:
            d[label] = {"path": str(p), "error": f"{type(e).__name__}:{e}"}
    return d

def _cgroups():
    cg = {"self_cgroup": _read_text(Path("/proc/self/cgroup"), 50_000), "mountinfo": _read_text(Path("/proc/self/mountinfo"), 200_000)}
    root = Path("/sys/fs/cgroup")
    if root.exists():
        for rel in ("cgroup.controllers","cgroup.subtree_control","cpu.max","cpu.weight","memory.max","memory.current","memory.high","pids.max","pids.current"):
            p = root / rel
            if p.exists(): cg[rel] = _read_text(p, 50_000).strip()
        # v1 common paths
        for rel in ("memory/memory.limit_in_bytes","memory/memory.usage_in_bytes","cpu/cpu.cfs_quota_us","cpu/cpu.cfs_period_us","pids/pids.max","pids/pids.current"):
            p = root / rel
            if p.exists(): cg["v1_"+rel.replace("/","_")] = _read_text(p, 50_000).strip()
    return cg

def _proc_snapshot():
    # Prefer ps with args; tolerate busybox variants.
    cmds = [
        ["ps","-eo","pid,ppid,pgid,sid,stat,etime,rss,vsz,comm,args","--forest"],
        ["ps","-eo","pid,ppid,stat,etime,rss,vsz,comm,args"],
        ["ps","auxww"],
    ]
    for c in cmds:
        r = _run(c, timeout=5)
        if r.get("returncode") == 0 and r.get("stdout"): return {"ps": r}
    return {"ps": r}

def collect(extra: dict | None = None) -> dict:
    cwd = Path.cwd()
    root = Path(__file__).resolve().parents[2] if len(Path(__file__).resolve().parents) >= 3 else cwd
    t = {
        "ts": _now(),
        "host": {"hostname": socket.gethostname(), "fqdn": socket.getfqdn()},
        "platform": {"system": platform.system(), "release": platform.release(), "version": platform.version(), "machine": platform.machine()},
        "python": {"executable": sys.executable, "version": sys.version, "argv": sys.argv},
        "paths": {"cwd": str(cwd), "script": str(Path(__file__).resolve()), "project_root": str(root)},
        "user": {"uid": getattr(os, "getuid", lambda: None)(), "gid": getattr(os, "getgid", lambda: None)()},
        "env": _env_redacted(),
        "cpu": {"count": os.cpu_count(), "proc_cpuinfo": _read_text(Path("/proc/cpuinfo"), 200_000)},
        "memory": {"proc_meminfo": _read_text(Path("/proc/meminfo"), 200_000)},
        "ulimits": _rlimits(),
        "ulimit_a": _run(["bash","-lc","ulimit -a"], timeout=5),
        "disk": _disk({"cwd": cwd, "project_root": root, "rootfs": Path("/")}),
        "df": _run(["df","-h"], timeout=5),
        "cgroups": _cgroups(),
        "proc": _proc_snapshot(),
        "probes": {"id": _run(["id"], timeout=5), "uname": _run(["uname","-a"], timeout=5)},
    }
    if extra: t["extra"] = extra
    return t

def write_logs(extra: dict | None = None, out_dir: Path | None = None, prefix: str = "telemetry") -> Path:
    root = Path(__file__).resolve().parents[2] if len(Path(__file__).resolve().parents) >= 3 else Path.cwd()
    out = out_dir or (root / "outputs" / "qa" / "logs")
    out.mkdir(parents=True, exist_ok=True)
    ts = _now()
    data = collect(extra=extra)
    jpath = out / f"{prefix}_{ts}.json"
    tpath = out / f"{prefix}_{ts}.txt"
    jpath.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        f"ts={data.get('ts')}",
        f"cwd={data['paths']['cwd']}",
        f"project_root={data['paths']['project_root']}",
        f"python={data['python']['executable']}",
        f"cpu_count={data['cpu'].get('count')}",
        f"hostname={data['host'].get('hostname')}",
        f"disk_cwd_free={data['disk'].get('cwd',{}).get('free')}",
        f"cgroup_memory_max={data['cgroups'].get('memory.max') or data['cgroups'].get('v1_memory_memory.limit_in_bytes')}",
        f"ps_rc={data.get('proc',{}).get('ps',{}).get('returncode')}",
    ]
    tpath.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return jpath

def main():
    extra = {"note": "telemetry standalone run"}
    p = write_logs(extra=extra)
    print(str(p))

if __name__ == "__main__":
    main()
