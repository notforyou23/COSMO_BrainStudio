#!/usr/bin/env python3
from __future__ import annotations
import os, sys, json, time, subprocess, hashlib, re, platform, shutil, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INC_ROOT = ROOT / "runtime" / "_build" / "incident_reports"

def ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())

def run(cmd, *, cwd=None, env=None, timeout=None, capture=True):
    t0 = time.time()
    p = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=capture)
    dt = time.time() - t0
    return {"cmd": cmd, "returncode": p.returncode, "stdout": p.stdout or "", "stderr": p.stderr or "", "seconds": dt}

def write_text(p: Path, s: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8", errors="replace")

def write_json(p: Path, obj):
    write_text(p, json.dumps(obj, indent=2, sort_keys=True) + "\n")

def host_snapshot():
    du = shutil.disk_usage(str(ROOT))
    return {
        "timestamp_utc": ts(),
        "cwd": str(Path.cwd()),
        "root": str(ROOT),
        "python": sys.version.replace("\n"," "),
        "executable": sys.executable,
        "platform": platform.platform(),
        "uname": getattr(platform, "uname")()._asdict() if hasattr(platform, "uname") else {},
        "env_subset": {k: os.environ.get(k,"") for k in sorted(set([
            "CI","GITHUB_ACTIONS","GITHUB_RUN_ID","GITHUB_SHA","GITHUB_REF",
            "BUILD_NUMBER","RUNNER_OS","RUNNER_NAME","HOME","PATH","DOCKER_HOST"
        ]))},
        "loadavg": os.getloadavg() if hasattr(os, "getloadavg") else None,
        "disk_usage_root": {"total": du.total, "used": du.used, "free": du.free},
    }

_NORM_RE = [
    (re.compile(r"\b[0-9a-f]{12,64}\b", re.I), "<HEX>"),
    (re.compile(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?\b"), "<TS>"),
    (re.compile(r"\b\d+\.\d+s\b"), "<SECS>"),
    (re.compile(r"\b\d+ms\b"), "<MS>"),
    (re.compile(r"\bpid=\d+\b", re.I), "pid=<N>"),
]

def norm(s: str) -> str:
    s = s.replace("\r\n","\n")
    for r, rep in _NORM_RE:
        s = r.sub(rep, s)
    return s.strip()

def signature(exit_code: int, logs: str) -> str:
    payload = f"exit={exit_code}\n{norm(logs)[-10000:]}"
    return hashlib.sha256(payload.encode("utf-8", errors="replace")).hexdigest()[:16]

def incident_dir(sig: str) -> Path:
    d = INC_ROOT / f"{time.strftime('%Y%m%d_%H%M%S', time.gmtime())}_preflight_{sig}"
    d.mkdir(parents=True, exist_ok=True)
    return d

def main() -> int:
    if os.environ.get("PREFLIGHT_REPRO_DISABLE","").lower() in {"1","true","yes"}:
        print("preflight_repro: disabled via PREFLIGHT_REPRO_DISABLE=1", file=sys.stderr)
        return 0

    pre = {"started_utc": ts(), "argv": sys.argv}
    dockerfile = ROOT / "docker" / "preflight" / "Dockerfile"
    image = os.environ.get("PREFLIGHT_REPRO_IMAGE", "cosmo-preflight-repro:local")
    build_ctx = dockerfile.parent if dockerfile.exists() else ROOT
    container = f"preflight_repro_{int(time.time())}"

    # Baseline diagnostics (kept even on early failures)
    base = {"host": host_snapshot()}
    dver = run(["docker","version"])
    dinfo = run(["docker","info"])
    base["docker_version_rc"] = dver["returncode"]
    base["docker_info_rc"] = dinfo["returncode"]

    if dver["returncode"] != 0:
        sig = signature(127, dver["stderr"] + dver["stdout"])
        inc = incident_dir(sig)
        write_json(inc/"summary.json", {"signature": sig, "phase": "docker_version", "returncode": dver["returncode"], **base, "docker_version": dver})
        write_text(inc/"docker_version.txt", dver["stdout"] + dver["stderr"])
        print(f"preflight_repro: FAIL signature={sig} phase=docker_version rc={dver['returncode']}", file=sys.stderr)
        return 2

    inc = None
    try:
        sig0 = signature(0, "")
        inc = incident_dir(sig0)
        write_json(inc/"baseline.json", base)
        write_text(inc/"docker_version.txt", dver["stdout"] + dver["stderr"])
        write_text(inc/"docker_info.txt", dinfo["stdout"] + dinfo["stderr"])
        write_text(inc/"docker_ps.txt", run(["docker","ps","-a","--no-trunc"])["stdout"])
        write_text(inc/"docker_images.txt", run(["docker","images","--digests","--no-trunc"])["stdout"])

        # Build image if Dockerfile exists, else expect image already present
        build_res = None
        if dockerfile.exists():
            build_cmd = ["docker","build","-f",str(dockerfile),"-t",image,str(build_ctx)]
            build_res = run(build_cmd)
            write_text(inc/"docker_build.txt", build_res["stdout"] + build_res["stderr"])
            if build_res["returncode"] != 0:
                sig = signature(build_res["returncode"], build_res["stdout"] + build_res["stderr"])
                inc2 = incident_dir(sig)
                for f in inc.iterdir():
                    if f.is_file():
                        write_text(inc2/f.name, f.read_text(encoding="utf-8", errors="replace"))
                write_json(inc2/"summary.json", {"signature": sig, "phase": "docker_build", "returncode": build_res["returncode"], "image": image, "dockerfile": str(dockerfile)})
                print(f"preflight_repro: FAIL signature={sig} phase=docker_build rc={build_res['returncode']}", file=sys.stderr)
                return 3

        # Run container and capture logs/inspect/stats
        env_args = []
        for k in ["CI","GITHUB_SHA","GITHUB_RUN_ID","PREFLIGHT_REPRO_MODE"]:
            if k in os.environ:
                env_args += ["-e", f"{k}={os.environ[k]}"]
        run_cmd = ["docker","run","--name",container,"--rm"] + env_args + [image]
        run_res = run(run_cmd)
        write_text(inc/"docker_run.txt", f"CMD: {' '.join(run_cmd)}\n\n" + run_res["stdout"] + run_res["stderr"])

        # Best-effort logs/inspect even with --rm (may fail)
        logs_res = run(["docker","logs",container])
        insp_res = run(["docker","inspect",container])
        stats_res = run(["docker","stats","--no-stream",container])
        write_text(inc/"container_logs.txt", logs_res["stdout"] + logs_res["stderr"])
        write_text(inc/"container_stats.txt", stats_res["stdout"] + stats_res["stderr"])
        write_text(inc/"container_inspect.json", insp_res["stdout"] + insp_res["stderr"])

        exit_code = run_res["returncode"]
        combined = (run_res["stdout"] + "\n" + run_res["stderr"] + "\n" + logs_res["stdout"] + logs_res["stderr"]).strip()
        sig = signature(exit_code, combined)
        # Rename dir to include final signature (create new and copy files, deterministic & cross-filesystem safe)
        final_dir = incident_dir(sig)
        for f in inc.iterdir():
            if f.is_file():
                write_text(final_dir/f.name, f.read_text(encoding="utf-8", errors="replace"))
        write_text(final_dir/"signature.txt", sig + "\n")
        write_json(final_dir/"summary.json", {
            "signature": sig, "phase": "docker_run", "image": image, "container": container,
            "returncode": exit_code, "started_utc": pre["started_utc"], "finished_utc": ts(),
            "dockerfile": str(dockerfile) if dockerfile.exists() else None,
        })
        if exit_code != 0:
            print(f"preflight_repro: FAIL signature={sig} phase=docker_run rc={exit_code}", file=sys.stderr)
            return 10
        print(f"preflight_repro: OK signature={sig} rc=0")
        return 0
    except Exception as e:
        tb = traceback.format_exc()
        sig = signature(99, str(e) + "\n" + tb)
        d = incident_dir(sig)
        write_text(d/"exception.txt", tb)
        write_json(d/"summary.json", {"signature": sig, "phase": "exception", "error": str(e), "started_utc": pre["started_utc"], "finished_utc": ts()})
        print(f"preflight_repro: FAIL signature={sig} phase=exception", file=sys.stderr)
        return 99
    finally:
        # Cleanup best-effort (in case --rm didn't execute)
        run(["docker","rm","-f",container], capture=True)

if __name__ == "__main__":
    raise SystemExit(main())
