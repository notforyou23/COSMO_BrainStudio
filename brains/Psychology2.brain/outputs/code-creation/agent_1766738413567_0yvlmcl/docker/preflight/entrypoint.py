#!/usr/bin/env python3
import argparse
import json
import os
import platform
import resource
import signal
import sys
import time
from datetime import datetime, timezone

def utc_ts():
    return datetime.now(timezone.utc).isoformat()

def _read_proc_status():
    p = "/proc/self/status"
    out = {}
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if ":" in line:
                    k, v = line.split(":", 1)
                    out[k.strip()] = v.strip()
    except Exception:
        return None
    return out

def mem_rss_kb():
    st = _read_proc_status()
    if st and "VmRSS" in st:
        try:
            return int(st["VmRSS"].split()[0])
        except Exception:
            pass
    try:
        r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if sys.platform.startswith("linux"):
            return int(r)
        return int(r)  # macOS already in KB, Linux is KB for ru_maxrss in Python docs? keep best-effort
    except Exception:
        return None

def cpu_times():
    try:
        ru = resource.getrusage(resource.RUSAGE_SELF)
        return {"user_s": ru.ru_utime, "sys_s": ru.ru_stime}
    except Exception:
        return None

def loadavg():
    try:
        la = os.getloadavg()
        return {"1m": la[0], "5m": la[1], "15m": la[2]}
    except Exception:
        return None

def log(event, **fields):
    payload = {"ts": utc_ts(), "event": event, **fields}
    sys.stdout.write(json.dumps(payload, sort_keys=True) + "\n")
    sys.stdout.flush()

def burn_cpu(seconds, quantum_s=0.2):
    t_end = time.monotonic() + max(0.0, seconds)
    x = 0
    while time.monotonic() < t_end:
        t_q = min(quantum_s, t_end - time.monotonic())
        t2 = time.monotonic() + max(0.0, t_q)
        while time.monotonic() < t2:
            x = (x * 1664525 + 1013904223) & 0xFFFFFFFF
    return x

def alloc_mem_mb(mb):
    if mb <= 0:
        return []
    chunk = b"x" * (1024 * 1024)
    blocks = []
    for _ in range(mb):
        blocks.append(bytearray(chunk))
    return blocks

def main():
    ap = argparse.ArgumentParser(description="Deterministic preflight entrypoint with periodic diagnostics.")
    ap.add_argument("--duration-s", type=float, default=float(os.environ.get("PREFLIGHT_DURATION_S", "20")))
    ap.add_argument("--interval-s", type=float, default=float(os.environ.get("PREFLIGHT_INTERVAL_S", "2")))
    ap.add_argument("--fail-mode", default=os.environ.get("PREFLIGHT_FAIL_MODE", "none"),
                    choices=["none", "exit", "exception", "sigterm", "sigkill", "oom"])
    ap.add_argument("--fail-after-s", type=float, default=float(os.environ.get("PREFLIGHT_FAIL_AFTER_S", "0")))
    ap.add_argument("--exit-code", type=int, default=int(os.environ.get("PREFLIGHT_EXIT_CODE", "42")))
    ap.add_argument("--cpu-burn-s", type=float, default=float(os.environ.get("PREFLIGHT_CPU_BURN_S", "0")))
    ap.add_argument("--mem-mb", type=int, default=int(os.environ.get("PREFLIGHT_MEM_MB", "0")))
    ap.add_argument("--signature", default=os.environ.get("PREFLIGHT_SIGNATURE", "PREFLIGHT_INCIDENT"))
    args = ap.parse_args()

    start = time.monotonic()
    log("start",
        pid=os.getpid(),
        ppid=os.getppid(),
        argv=sys.argv,
        cwd=os.getcwd(),
        python=sys.version,
        platform=platform.platform(),
        duration_s=args.duration_s,
        interval_s=args.interval_s,
        fail_mode=args.fail_mode,
        fail_after_s=args.fail_after_s,
        exit_code=args.exit_code,
        cpu_burn_s=args.cpu_burn_s,
        mem_mb=args.mem_mb,
        signature=args.signature,
        env_hint={k: os.environ.get(k) for k in [
            "CI", "GITHUB_ACTIONS", "RUNNER_OS", "HOSTNAME", "PREFLIGHT_FAIL_MODE"
        ] if k in os.environ})

    blocks = []
    if args.mem_mb:
        try:
            log("alloc_mem_begin", mem_mb=args.mem_mb)
            blocks = alloc_mem_mb(args.mem_mb)
            log("alloc_mem_done", mem_mb=args.mem_mb, rss_kb=mem_rss_kb())
        except MemoryError:
            log("alloc_mem_error", error="MemoryError", mem_mb=args.mem_mb, rss_kb=mem_rss_kb(), signature=args.signature)
            sys.exit(args.exit_code)

    next_tick = 0.0
    last_cpu_burn = 0
    fail_at = args.fail_after_s if args.fail_after_s and args.fail_after_s > 0 else None

    while True:
        elapsed = time.monotonic() - start
        if elapsed >= args.duration_s:
            break
        if elapsed >= next_tick:
            log("tick",
                elapsed_s=round(elapsed, 6),
                rss_kb=mem_rss_kb(),
                cpu=cpu_times(),
                loadavg=loadavg())
            next_tick += max(0.1, args.interval_s)

        if fail_at is not None and elapsed >= fail_at:
            log("fail_trigger", elapsed_s=round(elapsed, 6), fail_mode=args.fail_mode, signature=args.signature)
            sys.stdout.write(args.signature + "\n")
            sys.stdout.flush()
            if args.fail_mode == "exit":
                sys.exit(args.exit_code)
            if args.fail_mode == "exception":
                raise RuntimeError(args.signature)
            if args.fail_mode == "sigterm":
                os.kill(os.getpid(), signal.SIGTERM)
            if args.fail_mode == "sigkill":
                os.kill(os.getpid(), signal.SIGKILL)
            if args.fail_mode == "oom":
                # Deterministic-ish: allocate in chunks until MemoryError or limit reached.
                try:
                    for i in range(1, 65536):
                        blocks.append(bytearray(b"x" * (1024 * 1024)))
                        if i % 128 == 0:
                            log("oom_alloc_progress", added_mb=i, rss_kb=mem_rss_kb())
                except MemoryError:
                    log("oom_memoryerror", rss_kb=mem_rss_kb(), signature=args.signature)
                    sys.exit(args.exit_code)
                sys.exit(args.exit_code)

        if args.cpu_burn_s and last_cpu_burn == 0:
            last_cpu_burn = burn_cpu(args.cpu_burn_s)
            log("cpu_burn_done", cpu_burn_s=args.cpu_burn_s, checksum=last_cpu_burn, rss_kb=mem_rss_kb())

        time.sleep(0.05)

    log("complete", elapsed_s=round(time.monotonic() - start, 6), rss_kb=mem_rss_kb(), signature=args.signature)
    sys.exit(0)

if __name__ == "__main__":
    main()
