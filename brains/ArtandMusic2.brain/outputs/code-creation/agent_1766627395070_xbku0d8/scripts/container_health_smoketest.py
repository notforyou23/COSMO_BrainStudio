#!/usr/bin/env python3
import argparse, json, os, platform, shutil, subprocess, sys, time, traceback
from pathlib import Path

BASE_DIR = Path(os.environ.get("WORKDIR", "/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution")).resolve()

def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime())

def _read_text(p, n=200_000):
    try:
        s = Path(p).read_text(encoding="utf-8", errors="replace")
        return s[:n]
    except Exception:
        return None

def _disk_usage(path):
    try:
        u = shutil.disk_usage(str(path))
        return {"total": u.total, "used": u.used, "free": u.free}
    except Exception:
        return None

def _proc_stat():
    info = {"ts": _now(), "pid": os.getpid()}
    try:
        import resource
        ru = resource.getrusage(resource.RUSAGE_SELF)
        info["rusage"] = {"utime_s": ru.ru_utime, "stime_s": ru.ru_stime, "maxrss_kb": getattr(ru, "ru_maxrss", None)}
    except Exception:
        info["rusage_error"] = traceback.format_exc(limit=2)
    info["loadavg"] = None
    try:
        la = os.getloadavg()
        info["loadavg"] = {"1m": la[0], "5m": la[1], "15m": la[2]}
    except Exception:
        pass
    info["disk_usage"] = _disk_usage(BASE_DIR)
    meminfo = _read_text("/proc/meminfo", n=50_000)
    if meminfo:
        info["proc_meminfo_head"] = "\n".join(meminfo.splitlines()[:25])
    cgroup_mem = _read_text("/sys/fs/cgroup/memory.max", n=10_000) or _read_text("/sys/fs/cgroup/memory/memory.limit_in_bytes", n=10_000)
    if cgroup_mem:
        info["cgroup_memory_limit_raw"] = cgroup_mem.strip()
    cgroup_cpu = _read_text("/sys/fs/cgroup/cpu.max", n=10_000) or _read_text("/sys/fs/cgroup/cpu/cpu.cfs_quota_us", n=10_000)
    if cgroup_cpu:
        info["cgroup_cpu_limit_raw"] = cgroup_cpu.strip()
    return info

def _env_snapshot(extra=None):
    snap = {
        "ts": _now(),
        "python": {"executable": sys.executable, "version": sys.version, "path0": sys.path[0]},
        "platform": {"system": platform.system(), "release": platform.release(), "machine": platform.machine(), "platform": platform.platform()},
        "process": {"pid": os.getpid(), "ppid": os.getppid(), "cwd": str(Path.cwd()), "uid": getattr(os, "getuid", lambda: None)(), "gid": getattr(os, "getgid", lambda: None)()},
        "env": {k: os.environ.get(k) for k in sorted(os.environ) if k.startswith(("CI", "GITHUB", "RUNNER", "PYTHON", "PIP", "PATH", "HOME", "USER", "SHELL", "LANG", "LC_", "TZ", "CUDA", "NVIDIA", "OMP", "MKL", "KMP"))},
        "resources": _proc_stat(),
    }
    if extra:
        snap["extra"] = extra
    return snap

def _load_expectations(path, env_json):
    if env_json:
        try:
            v = json.loads(env_json)
            if isinstance(v, dict):
                v = v.get("required", [])
            if isinstance(v, list):
                return [{"path": str(x), "must_exist": True} if isinstance(x, str) else x for x in v]
        except Exception:
            return None
    if path:
        try:
            obj = json.loads(Path(path).read_text(encoding="utf-8"))
            v = obj.get("required", obj) if isinstance(obj, dict) else obj
            if isinstance(v, list):
                return [{"path": str(x), "must_exist": True} if isinstance(x, str) else x for x in v]
        except Exception:
            return None
    return None

def _validate_artifacts(out_dir, expectations):
    missing, bad = [], []
    for rule in expectations or []:
        p = Path(out_dir) / str(rule.get("path", "")).lstrip("/").replace("..", "")
        must = rule.get("must_exist", True)
        min_bytes = rule.get("min_bytes", 0)
        if must and not p.exists():
            missing.append(str(p))
            continue
        if p.exists() and min_bytes:
            try:
                if p.stat().st_size < int(min_bytes):
                    bad.append({"path": str(p), "size": p.stat().st_size, "min_bytes": int(min_bytes)})
            except Exception:
                bad.append({"path": str(p), "error": "stat_failed"})
    return missing, bad

def run_attempt(cmd, out_dir, timeout_s):
    t0 = time.time()
    proc = {"cmd": cmd, "start_ts": _now(), "timeout_s": timeout_s}
    try:
        r = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True, text=True, timeout=timeout_s)
        proc.update({"returncode": r.returncode, "duration_s": round(time.time() - t0, 3), "timed_out": False})
        (Path(out_dir) / "stdout.txt").write_text(r.stdout or "", encoding="utf-8", errors="replace")
        (Path(out_dir) / "stderr.txt").write_text(r.stderr or "", encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired as e:
        proc.update({"returncode": 124, "duration_s": round(time.time() - t0, 3), "timed_out": True})
        (Path(out_dir) / "stdout.txt").write_text((e.stdout or "") if isinstance(e.stdout, str) else "", encoding="utf-8", errors="replace")
        (Path(out_dir) / "stderr.txt").write_text((e.stderr or "") if isinstance(e.stderr, str) else "", encoding="utf-8", errors="replace")
    except Exception:
        proc.update({"returncode": 125, "duration_s": round(time.time() - t0, 3), "timed_out": False, "exception": traceback.format_exc()})
        (Path(out_dir) / "stdout.txt").write_text("", encoding="utf-8")
        (Path(out_dir) / "stderr.txt").write_text(proc.get("exception", ""), encoding="utf-8", errors="replace")
    proc["end_ts"] = _now()
    return proc

def main():
    ap = argparse.ArgumentParser(description="Container health smoke test runner with capture + env/resource logging + retries + artifact enforcement.")
    ap.add_argument("--cmd", nargs=argparse.REMAINDER, help="Command to execute (default: python scripts/minimal_failing_case.py)")
    ap.add_argument("--out-dir", default=str(BASE_DIR / "artifacts" / "smoketest"), help="Directory for logs/artifacts")
    ap.add_argument("--attempts", type=int, default=int(os.environ.get("SMOKE_ATTEMPTS", "3")))
    ap.add_argument("--timeout-s", type=int, default=int(os.environ.get("SMOKE_TIMEOUT_S", "120")))
    ap.add_argument("--backoff-s", type=float, default=float(os.environ.get("SMOKE_BACKOFF_S", "1.0")))
    ap.add_argument("--backoff-mult", type=float, default=float(os.environ.get("SMOKE_BACKOFF_MULT", "2.0")))
    ap.add_argument("--artifact-expectations", default=os.environ.get("ARTIFACT_EXPECTATIONS", str(BASE_DIR / "scripts" / "artifact_expectations.json")))
    ap.add_argument("--expect-artifacts-json", default=os.environ.get("EXPECT_ARTIFACTS_JSON"))
    args = ap.parse_args()

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = args.cmd if args.cmd else [sys.executable, str((BASE_DIR / "scripts" / "minimal_failing_case.py").resolve())]
    expectations = _load_expectations(args.artifact_expectations, args.expect_artifacts_json)
    meta = {"ts": _now(), "base_dir": str(BASE_DIR), "out_dir": str(out_dir), "cmd": cmd, "attempts": args.attempts, "timeout_s": args.timeout_s, "expectations": expectations}
    (out_dir / "env.json").write_text(json.dumps(_env_snapshot(meta), indent=2, sort_keys=True), encoding="utf-8")

    backoff = max(0.0, float(args.backoff_s))
    last = None
    for i in range(1, max(1, args.attempts) + 1):
        attempt_dir = out_dir / f"attempt_{i}"
        attempt_dir.mkdir(parents=True, exist_ok=True)
        (attempt_dir / "pre_resources.json").write_text(json.dumps(_proc_stat(), indent=2, sort_keys=True), encoding="utf-8")

        proc = run_attempt(cmd, attempt_dir, args.timeout_s)
        (attempt_dir / "post_resources.json").write_text(json.dumps(_proc_stat(), indent=2, sort_keys=True), encoding="utf-8")
        (attempt_dir / "run.json").write_text(json.dumps(proc, indent=2, sort_keys=True), encoding="utf-8")

        missing, bad = _validate_artifacts(out_dir, expectations or [])
        status = {"attempt": i, "returncode": proc.get("returncode"), "timed_out": proc.get("timed_out"), "missing_artifacts": missing, "bad_artifacts": bad}
        (attempt_dir / "validation.json").write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")
        last = {"proc": proc, "validation": status}

        if (missing or bad) and proc.get("returncode") == 0:
            (out_dir / "FINAL.json").write_text(json.dumps({"result": "HARD_ESCALATION_MISSING_ARTIFACTS", "last": last}, indent=2, sort_keys=True), encoding="utf-8")
            print("HARD_ESCALATION: missing/invalid artifacts after success; see artifacts.")
            raise SystemExit(90)

        if proc.get("returncode") == 0 and not missing and not bad:
            (out_dir / "FINAL.json").write_text(json.dumps({"result": "PASS", "last": last}, indent=2, sort_keys=True), encoding="utf-8")
            print("PASS")
            return 0

        if i < args.attempts:
            time.sleep(backoff)
            backoff = backoff * float(args.backoff_mult) if args.backoff_mult else backoff

    # Final failure path
    missing, bad = _validate_artifacts(out_dir, expectations or [])
    result = "FAIL"
    code = int(last["proc"].get("returncode", 1)) if last else 1
    if missing or bad:
        result = "HARD_ESCALATION_MISSING_ARTIFACTS"
        code = 90
    (out_dir / "FINAL.json").write_text(json.dumps({"result": result, "last": last, "missing_artifacts": missing, "bad_artifacts": bad}, indent=2, sort_keys=True), encoding="utf-8")
    print(result)
    raise SystemExit(code)

if __name__ == "__main__":
    main()
