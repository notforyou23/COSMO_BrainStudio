#!/usr/bin/env python3
import contextlib, datetime as _dt, io, json, os, platform, subprocess, sys, tempfile, textwrap, time, traceback
from pathlib import Path

ROOT = Path(__file__).resolve()
# repo root guessed as 3 levels up: scripts/qa/smoke_repro.py -> repo/
REPO = ROOT.parents[2] if len(ROOT.parents) >= 3 else Path.cwd()
OUT_DIR = REPO / "outputs" / "qa" / "logs"
OUT_DIR.mkdir(parents=True, exist_ok=True)
TS = _dt.datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S-%fZ")
LOG_PATH = OUT_DIR / f"{TS}_smoke_repro.log"

class _Tee(io.TextIOBase):
    def __init__(self, *streams):
        self._streams = [s for s in streams if s]
    def write(self, s):
        for st in self._streams:
            try: st.write(s)
            except Exception: pass
        return len(s)
    def flush(self):
        for st in self._streams:
            try: st.flush()
            except Exception: pass

def _now():
    return _dt.datetime.utcnow().isoformat(timespec="milliseconds") + "Z"

def log(stage, msg, data=None, level="INFO"):
    line = f"[{_now()}] {level} {stage}: {msg}"
    print(line)
    if data is not None:
        print(json.dumps(data, sort_keys=True, ensure_ascii=False, default=str))

def _run(cmd, timeout=30):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
    return {"cmd": cmd, "returncode": p.returncode, "stdout": p.stdout[-8000:], "stderr": p.stderr[-8000:]}

def _try_import(mod):
    t0 = time.time()
    try:
        m = __import__(mod)
        path = getattr(m, "__file__", None)
        ver = getattr(m, "__version__", None)
        return {"module": mod, "ok": True, "seconds": round(time.time()-t0, 4), "file": path, "version": ver}
    except Exception:
        return {"module": mod, "ok": False, "seconds": round(time.time()-t0, 4), "error": traceback.format_exc()[-6000:]}
def main():
    exit_code = 0
    stage_failures = []
    try:
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            tee_out, tee_err = _Tee(sys.__stdout__, f), _Tee(sys.__stderr__, f)
            with contextlib.redirect_stdout(tee_out), contextlib.redirect_stderr(tee_err):
                log("STARTUP", "smoke_repro starting", {"script": str(ROOT), "repo_guess": str(REPO), "log_path": str(LOG_PATH)})
                log("META", "runtime metadata", {
                    "utc": _now(),
                    "cwd": os.getcwd(),
                    "argv": sys.argv,
                    "pid": os.getpid(),
                    "ppid": os.getppid() if hasattr(os, "getppid") else None,
                    "python_executable": sys.executable,
                    "python_version": sys.version,
                    "platform": platform.platform(),
                    "machine": platform.machine(),
                    "processor": platform.processor(),
                    "uname": platform.uname()._asdict() if hasattr(platform, "uname") else None,
                    "env_subset": {k: os.environ.get(k) for k in ["PATH","PYTHONPATH","VIRTUAL_ENV","CONDA_PREFIX","CONDA_DEFAULT_ENV","HOME","SHELL"]},
                })

                log("FILESYSTEM", "probe write/read/list under outputs")
                fs = {"ok": True}
                try:
                    tmpd = REPO / "outputs" / "qa" / "tmp"
                    tmpd.mkdir(parents=True, exist_ok=True)
                    p = tmpd / f"{TS}_fs_probe.txt"
                    payload = f"ts={TS}\nrepo={REPO}\ncwd={os.getcwd()}\n"
                    p.write_text(payload, encoding="utf-8")
                    back = p.read_text(encoding="utf-8")
                    fs.update({"tmp_dir": str(tmpd), "file": str(p), "bytes": len(payload), "read_ok": (back == payload),
                               "dir_files": sorted([q.name for q in tmpd.glob('*')])[:50]})
                    try: p.unlink()
                    except Exception: fs["cleanup_error"] = traceback.format_exc()[-2000:]
                except Exception:
                    fs = {"ok": False, "error": traceback.format_exc()[-6000:]}
                log("FILESYSTEM", "result", fs, level="INFO" if fs.get("ok") else "ERROR")
                if not fs.get("ok"):
                    stage_failures.append("FILESYSTEM")
                    exit_code = max(exit_code, 3)

                log("IMPORTS", "probe stdlib imports")
                stdlib = ["ssl","sqlite3","ctypes","multiprocessing","hashlib","json","urllib.request","email","xml.etree.ElementTree"]
                stdlib_res = [_try_import(m) for m in stdlib]
                log("IMPORTS", "stdlib results", {"results": stdlib_res})

                log("IMPORTS", "probe common third-party imports (may fail if not installed)")
                third = ["numpy","pandas","requests","PIL","torch","tensorflow","jax","scipy","sklearn","matplotlib"]
                third_res = [_try_import(m) for m in third]
                log("IMPORTS", "third-party results", {"results": third_res})

                log("SUBPROCESS", "probe launching child python")
                sub = {"ok": True}
                try:
                    r = _run([sys.executable, "-c", "import sys,os; print('subprocess_ok'); print(sys.executable); print(sys.version.split()[0]); print(os.getcwd())"], timeout=30)
                    sub.update(r)
                    sub["ok"] = (r["returncode"] == 0 and "subprocess_ok" in (r["stdout"] or ""))
                except Exception:
                    sub = {"ok": False, "error": traceback.format_exc()[-6000:]}
                log("SUBPROCESS", "result", sub, level="INFO" if sub.get("ok") else "ERROR")
                if not sub.get("ok"):
                    stage_failures.append("SUBPROCESS")
                    exit_code = max(exit_code, 4)

                log("PIP", "probe pip metadata (best-effort)")
                pip_meta = {"ok": True}
                try:
                    r = _run([sys.executable, "-m", "pip", "--version"], timeout=20)
                    pip_meta.update({"pip_version": r})
                    r2 = _run([sys.executable, "-m", "pip", "list", "--format=json"], timeout=30)
                    if r2["returncode"] == 0:
                        pkgs = json.loads(r2["stdout"] or "[]")
                        pip_meta["pip_list_count"] = len(pkgs)
                        pip_meta["pip_list_sample"] = pkgs[:20]
                    else:
                        pip_meta["pip_list_error"] = r2
                except Exception:
                    pip_meta = {"ok": False, "error": traceback.format_exc()[-6000:]}
                log("PIP", "result", pip_meta, level="INFO" if pip_meta.get("ok") else "ERROR")

                log("SUMMARY", "stages complete", {"exit_code": exit_code, "failures": stage_failures, "log_path": str(LOG_PATH)})
    except Exception:
        try:
            sys.__stderr__.write("FATAL: unable to write log or crashed early\n")
            sys.__stderr__.write(traceback.format_exc() + "\n")
            sys.__stderr__.write(f"intended_log_path={LOG_PATH}\n")
        finally:
            return 2
    return exit_code

if __name__ == "__main__":
    raise SystemExit(main())
