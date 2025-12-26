#!/usr/bin/env python3
import os, sys, json, time, platform, socket, traceback
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
QA_DIR = BASE_DIR / "outputs" / "qa"

def _read_text(p):
    try:
        return Path(p).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

def _cgroup_read_first(*paths):
    for p in paths:
        t = _read_text(p)
        if t is not None:
            return t.strip()
    return None

def _parse_mem_bytes():
    # cgroup v2: memory.max ; v1: memory.limit_in_bytes
    raw = _cgroup_read_first("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes")
    if not raw:
        return None
    if raw.lower() == "max":
        return None
    try:
        return int(raw)
    except Exception:
        return None

def _parse_cpu_quota():
    # cgroup v2: cpu.max -> "quota period" ; v1: cpu.cfs_quota_us & cpu.cfs_period_us
    cpu_max = _cgroup_read_first("/sys/fs/cgroup/cpu.max")
    if cpu_max:
        parts = cpu_max.split()
        if len(parts) >= 2 and parts[0] != "max":
            try:
                quota = int(parts[0]); period = int(parts[1])
                return quota / period if period > 0 else None
            except Exception:
                return None
        return None
    q = _cgroup_read_first("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
    p = _cgroup_read_first("/sys/fs/cgroup/cpu/cpu.cfs_period_us")
    try:
        qv = int(q) if q else None
        pv = int(p) if p else None
        if qv is None or pv is None or qv < 0 or pv <= 0:
            return None
        return qv / pv
    except Exception:
        return None

def _disk_free_bytes(path):
    try:
        st = os.statvfs(str(path))
        return st.f_bavail * st.f_frsize
    except Exception:
        return None

class Tee:
    def __init__(self, *streams):
        self.streams = streams
    def write(self, s):
        for st in self.streams:
            try:
                st.write(s)
                st.flush()
            except Exception:
                pass
        return len(s)
    def flush(self):
        for st in self.streams:
            try:
                st.flush()
            except Exception:
                pass

def _env_subset(keys):
    out = {}
    for k in keys:
        if k in os.environ:
            v = os.environ.get(k)
            out[k] = v if (v is None or len(v) <= 500) else (v[:500] + "...(trunc)")
    return out

def collect_env(log_path):
    os_release = _read_text("/etc/os-release")
    mem_limit = _parse_mem_bytes()
    cpu_quota = _parse_cpu_quota()
    env_keys = [
        "HOSTNAME","KUBERNETES_SERVICE_HOST","KUBERNETES_PORT","KUBERNETES_NODE_NAME",
        "AWS_EXECUTION_ENV","ECS_CONTAINER_METADATA_URI","ECS_CONTAINER_METADATA_URI_V4",
        "CI","GITHUB_ACTIONS","GITLAB_CI","JENKINS_URL","BUILDKITE",
        "NVIDIA_VISIBLE_DEVICES","CUDA_VISIBLE_DEVICES","PYTHONPATH",
    ]
    return {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cwd": str(Path.cwd()),
        "base_dir": str(BASE_DIR),
        "qa_dir": str(QA_DIR),
        "log_path": str(log_path),
        "python": {"executable": sys.executable, "version": sys.version, "argv": sys.argv},
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "identity": {"hostname": socket.gethostname(), "fqdn": socket.getfqdn()},
        "os_release": os_release,
        "resources": {
            "cpu_count_os": os.cpu_count(),
            "cpu_quota_cores_cgroup": cpu_quota,
            "mem_limit_bytes_cgroup": mem_limit,
            "disk_free_bytes_qa_dir": _disk_free_bytes(QA_DIR),
        },
        "image_tag_heuristics": {
            "container_suspected": bool(_read_text("/.dockerenv")) or (os_release is not None and "container" in os_release.lower()),
            "cgroup": _read_text("/proc/1/cgroup"),
            "env": _env_subset(env_keys),
        },
    }

def main():
    ts = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    QA_DIR.mkdir(parents=True, exist_ok=True)
    log_path = QA_DIR / f"execution_smoketest_{ts}.log"
    env_path = QA_DIR / "execution_env.json"

    fails = []
    warns = []

    # Ensure we can write to QA_DIR early
    try:
        with open(log_path, "w", encoding="utf-8") as lf:
            orig_out, orig_err = sys.stdout, sys.stderr
            sys.stdout = Tee(orig_out, lf)
            sys.stderr = Tee(orig_err, lf)

            def _hook(exc_type, exc, tb):
                print("UNCAUGHT_EXCEPTION:", file=sys.stderr)
                traceback.print_exception(exc_type, exc, tb, file=sys.stderr)
                try: lf.flush()
                except Exception: pass
                sys.exit(2)

            sys.excepthook = _hook

            print(f"smoketest_start_utc={time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
            print(f"base_dir={BASE_DIR}")
            print(f"qa_dir={QA_DIR}")
            print(f"log_path={log_path}")

            # Minimal stability/compat checks (fail-safe)
            if sys.version_info < (3, 8):
                fails.append(f"python_version_unsupported:{sys.version_info.major}.{sys.version_info.minor}")
            if not QA_DIR.is_dir():
                fails.append("qa_dir_missing")
            try:
                probe = QA_DIR / ".write_probe"
                probe.write_text("ok", encoding="utf-8")
                probe.unlink(missing_ok=True)
            except Exception as e:
                fails.append(f"qa_dir_not_writable:{e.__class__.__name__}")

            # Basic runtime sanity: monotonic clock and deterministic math
            t0 = time.monotonic()
            time.sleep(0.01)
            t1 = time.monotonic()
            if not (t1 > t0):
                fails.append("monotonic_clock_not_increasing")

            try:
                import random
                def trial():
                    random.seed(1337)
                    s = 0.0
                    for i in range(20000):
                        s += (i % 97) * 0.0001
                    return round(s, 6)
                a, b, c = trial(), trial(), trial()
                if not (a == b == c):
                    fails.append(f"nondeterministic_basic_compute:{a},{b},{c}")
            except Exception as e:
                fails.append(f"basic_compute_failed:{e.__class__.__name__}")

            # Record environment
            env = collect_env(log_path)
            try:
                env_path.write_text(json.dumps(env, indent=2, sort_keys=True), encoding="utf-8")
                print(f"env_written={env_path}")
            except Exception as e:
                fails.append(f"env_write_failed:{e.__class__.__name__}")

            # Resource warnings (do not fail unless extreme)
            free = env.get("resources", {}).get("disk_free_bytes_qa_dir")
            if isinstance(free, int) and free < 50 * 1024 * 1024:
                warns.append(f"low_disk_free_bytes:{free}")
            mem = env.get("resources", {}).get("mem_limit_bytes_cgroup")
            if isinstance(mem, int) and mem > 0 and mem < 512 * 1024 * 1024:
                warns.append(f"low_mem_limit_bytes:{mem}")

            for w in warns:
                print("WARN:", w, file=sys.stderr)
            for f in fails:
                print("FAIL:", f, file=sys.stderr)

            print("smoketest_end_utc=" + time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
            try: lf.flush()
            except Exception: pass

            rc = 0 if not fails else 1
            return rc
    except Exception as e:
        try:
            sys.stderr.write(f"FATAL: could_not_initialize_logging:{e.__class__.__name__}\n")
        except Exception:
            pass
        return 2

if __name__ == "__main__":
    sys.exit(main())
