#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, os, platform, shutil, subprocess, sys, time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_PATH = ROOT / "runtime" / "_build" / "logs" / "container_health.jsonl"

def _now():
    return datetime.now(timezone.utc).isoformat()

def _disk_stats():
    try:
        du = shutil.disk_usage(str(ROOT))
        return {"total": du.total, "used": du.used, "free": du.free}
    except Exception as e:
        return {"error": repr(e)}

def _mem_stats():
    try:
        import psutil  # type: ignore
        vm = psutil.virtual_memory()
        return {"total": int(vm.total), "available": int(vm.available), "used": int(vm.used), "percent": float(vm.percent)}
    except Exception:
        pass
    try:
        if Path("/proc/meminfo").exists():
            info = {}
            for line in Path("/proc/meminfo").read_text().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    info[k.strip()] = v.strip()
            return {"proc_meminfo": {k: info.get(k) for k in ("MemTotal", "MemAvailable", "SwapTotal", "SwapFree") if k in info}}
    except Exception as e:
        return {"error": repr(e)}
    return {"note": "unavailable"}

def env_stats():
    return {
        "ts": _now(),
        "cwd": os.getcwd(),
        "root": str(ROOT),
        "python": sys.version.replace("\n", " "),
        "platform": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
        "disk": _disk_stats(),
        "memory": _mem_stats(),
    }

def ensure_log_dir():
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

def emit(record: dict):
    ensure_log_dir()
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")

def run_cmd(cmd, timeout=None, env=None, tail_lines=200):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, env=env)
    out_tail, err_tail = deque(maxlen=tail_lines), deque(maxlen=tail_lines)
    start = time.time()
    try:
        while True:
            if timeout and (time.time() - start) > timeout:
                p.kill()
                raise TimeoutError(f"timeout={timeout}s")
            o = p.stdout.readline() if p.stdout else ""
            e = p.stderr.readline() if p.stderr else ""
            if o: out_tail.append(o.rstrip("\n"))
            if e: err_tail.append(e.rstrip("\n"))
            if not o and not e and p.poll() is not None:
                break
        rc = p.wait()
        return rc, list(out_tail), list(err_tail), None
    except Exception as ex:
        try: p.kill()
        except Exception: pass
        return 124, list(out_tail), list(err_tail), repr(ex)

def retry(name, cmd, retries, delay_s, timeout=None):
    for attempt in range(1, retries + 2):
        rc, out_t, err_t, err = run_cmd(cmd, timeout=timeout)
        if rc == 0 and not err:
            return True, {"name": name, "attempt": attempt, "rc": rc}
        rec = {
            "type": "failure",
            "phase": name,
            "attempt": attempt,
            "cmd": cmd,
            "rc": rc,
            "error": err,
            "stdout_tail": out_t,
            "stderr_tail": err_t,
            "env": env_stats(),
        }
        emit(rec)
        if attempt <= retries:
            time.sleep(delay_s)
        else:
            return False, rec

def preflight(preflight_retries, delay_s):
    py = sys.executable
    scripts = ROOT / "scripts"
    cmds = []
    # Disk/memory check is in env_stats (always captured); still run tiny write test.
    cmds.append(("fs_smoke", [py, "-c", "import pathlib,os; p=pathlib.Path('._preflight_write'); p.write_text('ok'); p.unlink()"]))
    docker_sh = scripts / "docker_healthcheck.sh"
    if docker_sh.exists():
        cmds.append(("docker_healthcheck", ["bash", str(docker_sh)]))
    preflight_py = scripts / "preflight_diagnostics.py"
    if preflight_py.exists():
        cmds.append(("preflight_diagnostics", [py, str(preflight_py)]))
    smoke = scripts / "smoke_test.py"
    if smoke.exists():
        cmds.append(("smoke_test", [py, str(smoke)]))
    for name, cmd in cmds:
        ok, rec = retry(name, cmd, preflight_retries, delay_s, timeout=120)
        if not ok:
            rec["type"] = "preflight_failure"
            emit(rec)
            return False
    return True

def parse_args(argv):
    ap = argparse.ArgumentParser(description="Pipeline runner with preflight, retry, and structured failure logging.")
    ap.add_argument("--step", action="append", default=[], help="Command to run as a step (shell string). Repeatable.")
    ap.add_argument("--retries", type=int, default=int(os.getenv("PIPELINE_RETRIES", "1")))
    ap.add_argument("--preflight-retries", type=int, default=int(os.getenv("PREFLIGHT_RETRIES", "1")))
    ap.add_argument("--delay", type=float, default=float(os.getenv("PIPELINE_RETRY_DELAY_S", "2")))
    ap.add_argument("--tail-lines", type=int, default=int(os.getenv("PIPELINE_TAIL_LINES", "200")))
    ap.add_argument("--", dest="dashdash", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("cmd", nargs=argparse.REMAINDER, help="Command after -- to run as a single step.")
    return ap.parse_args(argv)

def main(argv):
    args = parse_args(argv)
    if not preflight(args.preflight_retries, args.delay):
        print("PRECHECK_FAILED (see logs)", file=sys.stderr)
        return 2
    steps = list(args.step)
    if args.cmd:
        steps.append(" ".join(args.cmd).strip())
    if not steps:
        print("No steps provided. Use --step or '-- <cmd>'.", file=sys.stderr)
        return 2

    for i, step in enumerate(steps, 1):
        cmd = ["bash", "-lc", step]
        for attempt in range(1, args.retries + 2):
            rc, out_t, err_t, err = run_cmd(cmd, timeout=None, tail_lines=args.tail_lines)
            if rc == 0 and not err:
                break
            rec = {
                "type": "step_failure",
                "step_index": i,
                "step": step,
                "attempt": attempt,
                "rc": rc,
                "error": err,
                "stdout_tail": out_t,
                "stderr_tail": err_t,
                "env": env_stats(),
            }
            emit(rec)
            if attempt <= args.retries:
                time.sleep(args.delay)
            else:
                print(f"STEP_FAILED index={i} rc={rc} (see logs)", file=sys.stderr)
                return rc if rc else 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
