#!/usr/bin/env python3
"""diagnose_container_loss.py

Collects environment diagnostics to help debug intermittent "Container lost" failures.
Writes a concise report under runtime/_build.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
BUILD_DIR = BASE_DIR / "runtime" / "_build"
BUILD_DIR.mkdir(parents=True, exist_ok=True)


def _read_text(path: str) -> str | None:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def _run(cmd: list[str], timeout: int = 20) -> dict:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return {"cmd": cmd, "returncode": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}
    except Exception as e:
        return {"cmd": cmd, "error": f"{type(e).__name__}: {e}"}


def _disk_info(path: Path) -> dict:
    try:
        u = shutil.disk_usage(path)
        return {
            "path": str(path),
            "total_bytes": u.total,
            "used_bytes": u.used,
            "free_bytes": u.free,
            "free_gb": round(u.free / (1024**3), 3),
        }
    except Exception as e:
        return {"path": str(path), "error": f"{type(e).__name__}: {e}"}


def _cgroup_limits() -> dict:
    out: dict = {}
    # cgroup v2
    for k, p in {
        "cgroup_v2_memory_max": "/sys/fs/cgroup/memory.max",
        "cgroup_v2_memory_current": "/sys/fs/cgroup/memory.current",
        "cgroup_v2_cpu_max": "/sys/fs/cgroup/cpu.max",
        "cgroup_v2_pids_max": "/sys/fs/cgroup/pids.max",
    }.items():
        t = _read_text(p)
        if t is not None:
            out[k] = t.strip()
    # cgroup v1 (common in some runtimes)
    for k, p in {
        "cgroup_v1_memory_limit_bytes": "/sys/fs/cgroup/memory/memory.limit_in_bytes",
        "cgroup_v1_memory_usage_bytes": "/sys/fs/cgroup/memory/memory.usage_in_bytes",
        "cgroup_v1_cpu_quota_us": "/sys/fs/cgroup/cpu/cpu.cfs_quota_us",
        "cgroup_v1_cpu_period_us": "/sys/fs/cgroup/cpu/cpu.cfs_period_us",
        "cgroup_v1_pids_max": "/sys/fs/cgroup/pids/pids.max",
    }.items():
        t = _read_text(p)
        if t is not None:
            out[k] = t.strip()
    return out


def _meminfo() -> dict:
    mi = _read_text("/proc/meminfo")
    if not mi:
        return {}
    out = {}
    for line in mi.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def _ulimits() -> dict:
    out = {}
    try:
        import resource  # type: ignore

        keys = [
            ("RLIMIT_AS", resource.RLIMIT_AS),
            ("RLIMIT_DATA", resource.RLIMIT_DATA),
            ("RLIMIT_FSIZE", resource.RLIMIT_FSIZE),
            ("RLIMIT_NOFILE", resource.RLIMIT_NOFILE),
            ("RLIMIT_NPROC", resource.RLIMIT_NPROC),
            ("RLIMIT_STACK", resource.RLIMIT_STACK),
            ("RLIMIT_CORE", resource.RLIMIT_CORE),
        ]
        for name, k in keys:
            try:
                soft, hard = resource.getrlimit(k)
                out[name] = {"soft": soft, "hard": hard}
            except Exception:
                pass
    except Exception:
        return out
    return out


def _import_smoke() -> dict:
    mods = [
        "json",
        "pathlib",
        "ssl",
        "hashlib",
        "sqlite3",
        "numpy",
        "pandas",
        "torch",
        "tensorflow",
        "sklearn",
        "PIL",
        "cv2",
        "matplotlib",
        "scipy",
        "requests",
    ]
    results = {}
    for m in mods:
        t0 = time.time()
        try:
            __import__(m)
            results[m] = {"ok": True, "ms": int((time.time() - t0) * 1000)}
        except Exception as e:
            results[m] = {"ok": False, "ms": int((time.time() - t0) * 1000), "error": f"{type(e).__name__}: {e}"}
    return results


def _pip_freeze(limit: int = 250) -> dict:
    r = _run([sys.executable, "-m", "pip", "freeze"], timeout=60)
    if "stdout" in r and r.get("returncode") == 0:
        lines = [ln for ln in r["stdout"].splitlines() if ln.strip()]
        r["count"] = len(lines)
        r["truncated"] = len(lines) > limit
        r["packages"] = lines[:limit]
        r.pop("stdout", None)
    return r


def main() -> int:
    report: dict = {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cwd": os.getcwd(),
        "base_dir": str(BASE_DIR),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "python_executable": sys.executable,
        },
        "env_subset": {k: os.environ.get(k) for k in [
            "CI", "GITHUB_ACTIONS", "RUNNER_OS", "PYTHONPATH", "PIP_DISABLE_PIP_VERSION_CHECK",
            "PIP_NO_CACHE_DIR", "PIP_DEFAULT_TIMEOUT", "VIRTUAL_ENV", "CONDA_PREFIX",
        ] if k in os.environ},
        "disk": {
            "base_dir": _disk_info(BASE_DIR),
            "build_dir": _disk_info(BUILD_DIR),
            "root": _disk_info(Path("/")),
        },
        "cgroup": _cgroup_limits(),
        "meminfo": _meminfo(),
        "ulimits": _ulimits(),
        "commands": {
            "python_V": _run([sys.executable, "-V"]),
            "pip_version": _run([sys.executable, "-m", "pip", "--version"]),
        },
        "pip_freeze": _pip_freeze(),
        "import_smoke": _import_smoke(),
    }

    json_path = BUILD_DIR / "execution_diagnostics_report.json"
    md_path = BUILD_DIR / "execution_diagnostics_report.md"

    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    # Concise markdown summary to spot resource/limit issues quickly.
    def g(d, *keys, default=None):
        cur = d
        for k in keys:
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                return default
        return cur

    lines = []
    lines.append("# Execution Diagnostics Report")
    lines.append("")
    lines.append(f"- Timestamp (UTC): `{report['timestamp_utc']}`")
    lines.append(f"- Python: `{g(report,'platform','python_version')}` (`{g(report,'platform','python_executable')}`)")
    lines.append(f"- Platform: `{g(report,'platform','platform')}`")
    lines.append("")
    lines.append("## Likely container-loss triggers to check")
    lines.append("")
    lines.append("- OOM: low cgroup memory limit, high import memory usage, large pip install build steps")
    lines.append("- Disk full: low free space in working dir")
    lines.append("- Too many open files / process limits: low ulimit settings")
    lines.append("- CPU quota/timeouts: constrained cpu.max / quota/period")
    lines.append("")
    lines.append("## Resource snapshot")
    lines.append("")
    bd = report["disk"]["base_dir"]
    lines.append(f"- Disk free (base_dir): `{bd.get('free_gb','?')} GB` (path `{bd.get('path')}`)")
    cg = report.get("cgroup", {})
    for k in ["cgroup_v2_memory_max", "cgroup_v2_cpu_max", "cgroup_v2_pids_max",
              "cgroup_v1_memory_limit_bytes", "cgroup_v1_cpu_quota_us", "cgroup_v1_pids_max"]:
        if k in cg:
            lines.append(f"- {k}: `{cg[k]}`")
    lines.append("")
    lines.append("## Import smoke test")
    lines.append("")
    sm = report.get("import_smoke", {})
    ok = [m for m, r in sm.items() if r.get("ok")]
    bad = [(m, sm[m].get("error")) for m in sm if not sm[m].get("ok")]
    lines.append(f"- OK: {len(ok)} modules")
    if bad:
        lines.append(f"- FAIL: {len(bad)} modules")
        for m, e in bad[:15]:
            lines.append(f"  - `{m}`: `{e}`")
        if len(bad) > 15:
            lines.append("  - (truncated)")
    else:
        lines.append("- FAIL: 0 modules")
    lines.append("")
    lines.append("## Next steps")
    lines.append("")
    lines.append("- If memory limit is low or `memory.max` is set, reduce parallelism and avoid source builds.")
    lines.append("- Prefer pinned wheels and deterministic builds (Docker) to prevent long installs/timeouts.")
    lines.append("- Re-run with: `python scripts/diagnose_container_loss.py` and attach the JSON report.")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"WROTE:{json_path.relative_to(BASE_DIR)}")
    print(f"WROTE:{md_path.relative_to(BASE_DIR)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
