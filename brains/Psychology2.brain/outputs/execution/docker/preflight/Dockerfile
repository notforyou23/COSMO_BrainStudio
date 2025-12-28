# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PREFLIGHT_SIGNATURE=PRELIGHT_REPRO_V1 \
    PREFLIGHT_EXIT_CODE=42 \
    PREFLIGHT_FAIL=1 \
    PREFLIGHT_SPIN_SECS=0.3

WORKDIR /app

RUN python - <<'PY'
from pathlib import Path
Path("repro.py").write_text(r'''
import json, os, platform, resource, sys, time

def ts():
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + f".{int((time.time()%1)*1000):03d}Z"

def read_first(path):
    try:
        with open(path, "rb") as f:
            return f.read(2048).decode("utf-8", "replace").strip()
    except Exception as e:
        return f"<unavailable:{e.__class__.__name__}:{e}>"

def meminfo():
    out = {}
    for line in read_first("/proc/meminfo").splitlines():
        parts = line.split()
        if len(parts) >= 2:
            out[parts[0].rstrip(":")] = parts[1]
    return out

def status_self():
    d = {}
    raw = read_first("/proc/self/status")
    for line in raw.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            k = k.strip()
            if k in ("VmRSS", "VmHWM", "VmSize", "Threads"):
                d[k] = v.strip()
    return d

def ru():
    try:
        r = resource.getrusage(resource.RUSAGE_SELF)
        return {
            "ru_utime": r.ru_utime,
            "ru_stime": r.ru_stime,
            "ru_maxrss_kb": getattr(r, "ru_maxrss", None),
            "ru_inblock": r.ru_inblock,
            "ru_oublock": r.ru_oublock,
            "ru_nvcsw": r.ru_nvcsw,
            "ru_nivcsw": r.ru_nivcsw,
        }
    except Exception as e:
        return {"error": f"{e.__class__.__name__}:{e}"}

def eprint(*a, **k):
    print(*a, file=sys.stderr, **k)

sig = os.getenv("PREFLIGHT_SIGNATURE", "PRELIGHT_REPRO_V1")
exit_code = int(os.getenv("PREFLIGHT_EXIT_CODE", "42"))
fail = os.getenv("PREFLIGHT_FAIL", "1").lower() not in ("0", "false", "no")
spin_secs = float(os.getenv("PREFLIGHT_SPIN_SECS", "0.3"))

payload = {
    "ts_start": ts(),
    "argv": sys.argv,
    "python": sys.version.replace("\n", " "),
    "platform": {
        "platform": platform.platform(),
        "uname": " ".join(platform.uname()),
        "machine": platform.machine(),
        "processor": platform.processor(),
    },
    "env_select": {k: os.getenv(k) for k in ("PREFLIGHT_SIGNATURE","PREFLIGHT_EXIT_CODE","PREFLIGHT_FAIL","PREFLIGHT_SPIN_SECS")},
    "proc": {
        "cpuinfo_head": read_first("/proc/cpuinfo"),
        "meminfo": meminfo(),
        "self_status": status_self(),
    },
}

print("PREFLIGHT_REPRO_BEGIN " + payload["ts_start"])
print("PREFLIGHT_REPRO_PAYLOAD_JSON " + json.dumps(payload, sort_keys=True))
eprint("PREFLIGHT_REPRO_STDERR_SENTINEL ts=" + ts())

t0 = time.time()
x = 0
while time.time() - t0 < spin_secs:
    x = (x * 1664525 + 1013904223) & 0xFFFFFFFF
print("PREFLIGHT_REPRO_SPIN_DONE x=%d elapsed=%.3f" % (x, time.time() - t0))

usage = ru()
print("PREFLIGHT_REPRO_RUSAGE_JSON " + json.dumps(usage, sort_keys=True))

if fail:
    eprint("PREFLIGHT_REPRO_FAIL signature=%s exit_code=%d ts=%s" % (sig, exit_code, ts()))
    eprint("PREFLIGHT_REPRO_SIGNATURE " + sig)
    sys.exit(exit_code)

print("PREFLIGHT_REPRO_OK signature=%s ts=%s" % (sig, ts()))
print("PREFLIGHT_REPRO_SIGNATURE " + sig)
sys.exit(0)
''', encoding="utf-8")
print("OK: wrote /app/repro.py")
PY

ENTRYPOINT ["python","/app/repro.py"]
