#!/usr/bin/env python3
from __future__ import annotations
import os, sys, json, time, shutil, platform, subprocess, tempfile
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path('/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution')
LOG_PATH = ROOT / 'runtime/_build/logs/container_health.jsonl'
DEFAULT_TAIL = int(os.getenv('PREFLIGHT_TAIL_LINES', '200'))
RETRIES = int(os.getenv('PREFLIGHT_RETRIES', '2'))
RETRY_DELAY_S = float(os.getenv('PREFLIGHT_RETRY_DELAY_S', '1.5'))
MIN_FREE_MB = int(os.getenv('PREFLIGHT_MIN_FREE_MB', '512'))
MIN_AVAIL_MEM_MB = int(os.getenv('PREFLIGHT_MIN_AVAIL_MEM_MB', '256'))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def tail_text(text: str, n: int = DEFAULT_TAIL) -> str:
    if not text:
        return ''
    lines = text.splitlines()
    return '\n'.join(lines[-max(1, n):])


def _try_int(x):
    try:
        return int(x)
    except Exception:
        return None


def mem_stats():
    stats = {"total_bytes": None, "available_bytes": None, "source": None}
    try:
        import psutil  # type: ignore
        vm = psutil.virtual_memory()
        stats.update(total_bytes=int(vm.total), available_bytes=int(getattr(vm, "available", None) or (vm.total - vm.used)), source="psutil")
        return stats
    except Exception:
        pass
    try:
        if sys.platform.startswith('linux') and Path('/proc/meminfo').is_file():
            kv = {}
            for line in Path('/proc/meminfo').read_text(encoding='utf-8', errors='ignore').splitlines():
                parts = line.split(':', 1)
                if len(parts) != 2:
                    continue
                k = parts[0].strip()
                v = parts[1].strip().split()
                if not v:
                    continue
                kv[k] = _try_int(v[0])
            total_kb = kv.get('MemTotal')
            avail_kb = kv.get('MemAvailable') or kv.get('MemFree')
            if total_kb:
                stats.update(total_bytes=int(total_kb) * 1024, available_bytes=(int(avail_kb) * 1024 if avail_kb else None), source="/proc/meminfo")
                return stats
    except Exception:
        pass
    try:
        if hasattr(os, "sysconf"):
            pages = os.sysconf("SC_PHYS_PAGES") if "SC_PHYS_PAGES" in os.sysconf_names else None
            page_size = os.sysconf("SC_PAGE_SIZE") if "SC_PAGE_SIZE" in os.sysconf_names else None
            if pages and page_size:
                stats.update(total_bytes=int(pages) * int(page_size), source="os.sysconf")
    except Exception:
        pass
    return stats


def env_stats():
    du = shutil.disk_usage(ROOT)
    ms = mem_stats()
    return {
        "timestamp": _utc_now(),
        "cwd": str(Path.cwd()),
        "root": str(ROOT),
        "python": {"executable": sys.executable, "version": sys.version.split()[0]},
        "platform": {"system": platform.system(), "release": platform.release(), "version": platform.version(), "machine": platform.machine()},
        "disk": {"path": str(ROOT), "total_bytes": int(du.total), "used_bytes": int(du.used), "free_bytes": int(du.free)},
        "memory": ms,
        "env": {
            "CI": os.getenv("CI"),
            "GITHUB_ACTIONS": os.getenv("GITHUB_ACTIONS"),
            "BUILD_ID": os.getenv("BUILD_ID"),
            "RUN_ID": os.getenv("RUN_ID"),
        },
    }


def write_failure(record: dict):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def run_cmd(cmd, timeout_s=120, env=None):
    p = subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout_s,
        shell=isinstance(cmd, str),
    )
    return p.returncode, p.stdout or "", p.stderr or ""


def retry_step(step_name: str, fn):
    last_err = None
    for attempt in range(1, RETRIES + 2):
        try:
            fn()
            return
        except Exception as e:
            last_err = e
            rec = {
                "event": "preflight_failure",
                "step": step_name,
                "attempt": attempt,
                "max_attempts": RETRIES + 1,
                "error": repr(e),
                "env_stats": env_stats(),
            }
            if isinstance(e, PreflightCmdError):
                rec.update({
                    "command": e.command,
                    "returncode": e.returncode,
                    "stdout_tail": tail_text(e.stdout),
                    "stderr_tail": tail_text(e.stderr),
                })
            write_failure(rec)
            if attempt <= RETRIES:
                time.sleep(RETRY_DELAY_S)
    raise last_err


class PreflightCmdError(RuntimeError):
    def __init__(self, message, command, returncode, stdout, stderr):
        super().__init__(message)
        self.command = command
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def step_disk_and_writable():
    du = shutil.disk_usage(ROOT)
    free_mb = du.free / (1024 * 1024)
    if free_mb < MIN_FREE_MB:
        raise RuntimeError(f"Insufficient disk free space at {ROOT}: {free_mb:.1f}MB < {MIN_FREE_MB}MB")
    tmp = ROOT / "runtime/_build/.preflight_write_test"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text("ok", encoding="utf-8")
    tmp.unlink(missing_ok=True)


def step_memory():
    ms = mem_stats()
    avail = ms.get("available_bytes")
    if avail is None:
        return
    avail_mb = avail / (1024 * 1024)
    if avail_mb < MIN_AVAIL_MEM_MB:
        raise RuntimeError(f"Low available memory: {avail_mb:.1f}MB < {MIN_AVAIL_MEM_MB}MB (source={ms.get('source')})")


def step_container_health_command():
    sh = ROOT / "scripts/docker_healthcheck.sh"
    if sh.is_file():
        cmd = ["bash", str(sh)]
        rc, out, err = run_cmd(cmd, timeout_s=60)
        if rc != 0:
            raise PreflightCmdError("Container health command failed", cmd, rc, out, err)
        return
    cmd = [sys.executable, "-c", "import sys,os,shutil; p=os.getcwd(); du=shutil.disk_usage(p); print('ok',sys.version.split()[0],du.free)"]
    rc, out, err = run_cmd(cmd, timeout_s=30)
    if rc != 0:
        raise PreflightCmdError("Fallback container health command failed", cmd, rc, out, err)


def step_smoke_test():
    py = ROOT / "scripts/smoke_test.py"
    if py.is_file():
        cmd = [sys.executable, str(py)]
        rc, out, err = run_cmd(cmd, timeout_s=120)
        if rc != 0:
            raise PreflightCmdError("Smoke test failed", cmd, rc, out, err)
        return
    code = "import json,ssl,hashlib,tempfile,os; d={'ok':True}; json.dumps(d); hashlib.sha256(b'x').hexdigest(); tf=tempfile.NamedTemporaryFile(delete=False); tf.write(b'1'); tf.close(); os.unlink(tf.name); print('smoke_ok')"
    cmd = [sys.executable, "-c", code]
    rc, out, err = run_cmd(cmd, timeout_s=30)
    if rc != 0:
        raise PreflightCmdError("Fallback smoke test failed", cmd, rc, out, err)


def main():
    steps = [
        ("disk_and_writable", step_disk_and_writable),
        ("memory", step_memory),
        ("container_health_command", step_container_health_command),
        ("smoke_test", step_smoke_test),
    ]
    for name, fn in steps:
        retry_step(name, fn)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(2)
