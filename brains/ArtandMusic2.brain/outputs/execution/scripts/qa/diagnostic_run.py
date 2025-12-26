from __future__ import annotations
import os, sys, json, time, uuid, shutil, platform, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "outputs" / "qa" / "logs"

def _run(cmd, *, capture=True, check=False, text=True, timeout=None):
    p = subprocess.run(cmd, capture_output=capture, text=text, timeout=timeout)
    if check and p.returncode != 0:
        raise RuntimeError(f"cmd failed {cmd}: rc={p.returncode}\n{p.stderr}")
    return p

def _w(path: Path, data: str, mode="w"):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, mode, encoding="utf-8", errors="replace") as f:
        f.write(data)

def _json(path: Path, obj):
    _w(path, json.dumps(obj, indent=2, sort_keys=True) + "\n")

def _which_docker():
    return shutil.which("docker") is not None

def collect_host_telemetry(outdir: Path):
    tel = {
        "ts": time.time(),
        "python": sys.version,
        "platform": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
        "cwd": str(Path.cwd()),
        "root": str(ROOT),
        "env": {k: os.environ.get(k) for k in ["CI","GITHUB_ACTIONS","RUNNER_OS","DOCKER_HOST","DOCKER_TLS_VERIFY","DOCKER_CERT_PATH"] if os.environ.get(k) is not None},
        "disk": {},
    }
    try:
        u = shutil.disk_usage(str(ROOT))
        tel["disk"] = {"total": u.total, "used": u.used, "free": u.free}
    except Exception as e:
        tel["disk_error"] = repr(e)
    for name, cmd in [
        ("docker_version", ["docker","version"]),
        ("docker_info", ["docker","info"]),
    ]:
        try:
            r = _run(cmd, capture=True, timeout=30)
            _w(outdir / f"{name}.txt", (r.stdout or "") + "\n" + (r.stderr or ""))
            tel[name + "_rc"] = r.returncode
        except Exception as e:
            tel[name + "_error"] = repr(e)
    _json(outdir / "host_telemetry.json", tel)
    return tel

def _docker_events(name: str, outpath: Path):
    outpath.parent.mkdir(parents=True, exist_ok=True)
    f = open(outpath, "w", encoding="utf-8", errors="replace")
    p = subprocess.Popen(["docker","events","--since","0s","--filter",f"container={name}"], stdout=f, stderr=subprocess.STDOUT, text=True)
    return p, f

def _safe(cmd):
    try: return _run(cmd, capture=True, timeout=20)
    except Exception as e: return type("R",(object,),{"returncode":-1,"stdout":"","stderr":repr(e)})()

def run_container_attempt(outdir: Path, *, image: str, mem: str|None, cpus: str|None, timeout_s: int, cmd: str, attempt: int):
    name = f"qa_diag_{uuid.uuid4().hex[:12]}"
    mount_root = str(ROOT)
    mount_outputs = str((ROOT / "outputs").resolve())
    flags = ["docker","create","--name",name,"-w","/work","-v",f"{mount_root}:/work:rw","-v",f"{mount_outputs}:/outputs:rw"]
    if mem: flags += ["--memory", mem, "--memory-swap", mem]
    if cpus: flags += ["--cpus", cpus]
    flags += [image, "bash","-lc", cmd]
    meta = {"attempt": attempt, "name": name, "image": image, "mem": mem, "cpus": cpus, "timeout_s": timeout_s, "cmd": cmd}
    _json(outdir / f"attempt_{attempt:02d}_meta.json", meta)
    create = _run(flags, capture=True)
    _w(outdir / f"attempt_{attempt:02d}_docker_create.txt", (create.stdout or "") + (create.stderr or ""))
    if create.returncode != 0:
        return {"ok": False, "stage": "create", "rc": create.returncode, "name": name}
    ev_p, ev_f = _docker_events(name, outdir / f"attempt_{attempt:02d}_events.txt")
    start_t = time.time()
    timed_out = False
    try:
        start = subprocess.run(["docker","start","-a",name], capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        timed_out = True
        _safe(["docker","kill",name])
        start = type("R",(object,),{"returncode":124,"stdout":"","stderr":"timeout"})()
    end_t = time.time()
    _w(outdir / f"attempt_{attempt:02d}_stdout.txt", start.stdout or "")
    _w(outdir / f"attempt_{attempt:02d}_stderr.txt", start.stderr or "")
    insp = _safe(["docker","inspect",name])
    _w(outdir / f"attempt_{attempt:02d}_inspect.json", insp.stdout or insp.stderr or "")
    logs = _safe(["docker","logs",name])
    _w(outdir / f"attempt_{attempt:02d}_docker_logs.txt", (logs.stdout or "") + (logs.stderr or ""))
    _safe(["docker","rm","-f",name])
    try:
        ev_p.terminate()
        ev_p.wait(timeout=2)
    except Exception:
        try: ev_p.kill()
        except Exception: pass
    try: ev_f.close()
    except Exception: pass
    res = {"ok": (start.returncode == 0 and not timed_out), "rc": start.returncode, "timed_out": timed_out, "elapsed_s": round(end_t-start_t, 3), "name": name}
    _json(outdir / f"attempt_{attempt:02d}_result.json", res)
    return res

def ensure_minimal_log_written():
    return (LOG_DIR / "minimal_ok.txt").exists() or (LOG_DIR / "minimal_ok.json").exists()

def main(argv=None):
    argv = argv or sys.argv[1:]
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    outdir = LOG_DIR / time.strftime("diag_%Y%m%d_%H%M%S")
    outdir.mkdir(parents=True, exist_ok=True)
    if not _which_docker():
        _w(outdir / "fatal.txt", "docker not found on PATH\n")
        print(str(outdir))
        return 2
    collect_host_telemetry(outdir)
    image = os.environ.get("QA_DIAG_IMAGE", "python:3.11-slim")
    _w(outdir / "plan.txt", "Attempts: python write -> pytest single file; remediations: longer timeout, more memory, no limits\n")
    minimal_py = "import pathlib, json, os; p=pathlib.Path('/outputs/qa/logs'); p.mkdir(parents=True, exist_ok=True); (p/'minimal_ok.txt').write_text('ok\n'); (p/'minimal_ok.json').write_text(json.dumps({'ok':True,'cwd':os.getcwd()}))"
    pytest_cmd = "python -c "import pathlib; p=pathlib.Path('/tmp/test_minimal.py'); p.write_text('def test_minimal():\n    assert 1==1\n');" && python -m pip -q show pytest >/dev/null 2>&1 || python -m pip -q install pytest >/dev/null 2>&1; python -m pytest -q /tmp/test_minimal.py -s"
    attempts = [
        {"mem": "1g", "cpus": None, "timeout_s": 120, "cmd": f"python -c {json.dumps(minimal_py)}"},
        {"mem": "1g", "cpus": None, "timeout_s": 180, "cmd": pytest_cmd},
        {"mem": "2g", "cpus": None, "timeout_s": 300, "cmd": pytest_cmd},
        {"mem": None, "cpus": None, "timeout_s": 600, "cmd": pytest_cmd},
    ]
    results = []
    for i, a in enumerate(attempts, 1):
        r = run_container_attempt(outdir, image=image, attempt=i, **a)
        results.append(r)
        if ensure_minimal_log_written():
            break
    _json(outdir / "summary.json", {"outdir": str(outdir), "results": results, "minimal_log_written": ensure_minimal_log_written()})
    print(str(outdir))
    return 0 if ensure_minimal_log_written() else 1

if __name__ == "__main__":
    raise SystemExit(main())
