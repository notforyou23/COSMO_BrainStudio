#!/usr/bin/env python3
import os, sys, time, json, platform, traceback, subprocess, signal, textwrap
from pathlib import Path

ROOT = Path(__file__).resolve()
for _ in range(6):
    if (ROOT / "outputs").exists() or (ROOT / "scripts").exists():
        break
    if ROOT.parent == ROOT:
        break
    ROOT = ROOT.parent
CWD = Path.cwd()

def utc_ts():
    t = time.time()
    s = time.strftime("%Y-%m-%dT%H-%M-%S", time.gmtime(t))
    ms = int((t - int(t)) * 1000)
    return f"{s}-{ms:03d}Z"

LOG_DIR = ROOT / "outputs" / "qa" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / f"{utc_ts()}_repro_smoke.log"

class Tee:
    def __init__(self, *streams):
        self.streams = streams
    def write(self, data):
        for s in self.streams:
            try:
                s.write(data)
                s.flush()
            except Exception:
                pass
    def flush(self):
        for s in self.streams:
            try: s.flush()
            except Exception: pass

_log_f = open(LOG_PATH, "w", encoding="utf-8", errors="replace")
sys.stdout = Tee(sys.__stdout__, _log_f)
sys.stderr = Tee(sys.__stderr__, _log_f)

def log(s=""):
    print(s)

def section(title):
    log("\n" + "="*80)
    log(title)
    log("="*80)

def safe_env():
    allow = ("PYTHON", "PATH", "HOME", "SHELL", "USER", "LANG", "LC_", "VIRTUAL_ENV", "CONDA", "PIP", "CUDA", "LD_", "DYLD_", "OPENAI", "HF_", "TRANSFORMERS", "TORCH", "TF_")
    redacts = ("KEY", "TOKEN", "SECRET", "PASSWORD", "PASS", "COOKIE", "BEARER", "AUTH")
    out = {}
    for k, v in os.environ.items():
        if k.upper().startswith(redacts) or any(r in k.upper() for r in redacts):
            continue
        if k.startswith(allow) or any(k.startswith(p) for p in allow if p.endswith("_")):
            out[k] = v
    return out

def run_subproc(args, timeout=20):
    t0 = time.time()
    try:
        cp = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        dt = time.time() - t0
        return {
            "args": args,
            "returncode": cp.returncode,
            "stdout": cp.stdout[-20000:],
            "stderr": cp.stderr[-20000:],
            "seconds": round(dt, 3),
            "signal": (-cp.returncode if cp.returncode < 0 else None),
        }
    except subprocess.TimeoutExpired as e:
        return {"args": args, "timeout": timeout, "stdout": (e.stdout or "")[-20000:], "stderr": (e.stderr or "")[-20000:], "returncode": None}
    except Exception as e:
        return {"args": args, "error": repr(e), "traceback": traceback.format_exc()}

def try_import(mod):
    t0 = time.time()
    ok, err = True, None
    try:
        __import__(mod)
    except Exception:
        ok, err = False, traceback.format_exc()
    return {"module": mod, "ok": ok, "seconds": round(time.time() - t0, 3), "error": err}

def fs_probe(base):
    res = {"base": str(base), "ok": True, "steps": []}
    try:
        base.mkdir(parents=True, exist_ok=True)
        p = base / f"fs_probe_{utc_ts()}.txt"
        p.write_text("ok\n", encoding="utf-8")
        res["steps"].append({"write": str(p), "bytes": p.stat().st_size})
        res["steps"].append({"listdir_count": len(list(base.glob('*')))})
        p.unlink(missing_ok=True)
    except Exception:
        res["ok"] = False
        res["error"] = traceback.format_exc()
    return res

def main():
    section("repro_smoke.py: STARTUP")
    log(f"LOG_PATH={LOG_PATH}")
    meta = {
        "timestamp_utc": utc_ts(),
        "pid": os.getpid(),
        "ppid": os.getppid(),
        "argv": sys.argv,
        "cwd": str(CWD),
        "root_guess": str(ROOT),
        "python": {"executable": sys.executable, "version": sys.version, "prefix": sys.prefix, "base_prefix": getattr(sys, "base_prefix", None)},
        "platform": {"platform": platform.platform(), "machine": platform.machine(), "processor": platform.processor(), "python_build": platform.python_build()},
        "env": safe_env(),
    }
    section("ENV METADATA (json)")
    log(json.dumps(meta, indent=2, sort_keys=True))

    section("CRASH BOUNDARY: FILESYSTEM")
    fs_results = [fs_probe(ROOT / "outputs" / "qa" / "logs"), fs_probe(ROOT / "outputs")]
    for r in fs_results:
        log(json.dumps(r, indent=2, sort_keys=True))

    section("CRASH BOUNDARY: IN-PROCESS IMPORTS")
    mods = ["json","ssl","sqlite3","numpy","pandas","PIL","cv2","torch","tensorflow","transformers","openai"]
    imp_results = [try_import(m) for m in mods]
    for r in imp_results:
        log(json.dumps(r, indent=2, sort_keys=True))

    section("CRASH BOUNDARY: SUBPROCESS IMPORTS (detect segfaults)")
    py = sys.executable or "python3"
    sp_mods = ["numpy","pandas","PIL","cv2","torch","tensorflow","transformers"]
    sp_results = []
    for m in sp_mods:
        code = f"import {m}; print('IMPORT_OK:{m}')"
        sp_results.append(run_subproc([py, "-c", code], timeout=30))
    for r in sp_results:
        log(json.dumps(r, indent=2, sort_keys=True))

    section("SUMMARY")
    summary = {
        "log_path": str(LOG_PATH),
        "fs_ok": all(r.get("ok") for r in fs_results),
        "imports_ok": {r["module"]: r["ok"] for r in imp_results},
        "subprocess_returncodes": [r.get("returncode") for r in sp_results],
        "subprocess_signals": [r.get("signal") for r in sp_results],
    }
    log(json.dumps(summary, indent=2, sort_keys=True))
    log("\nDONE")

if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException:
        section("UNHANDLED EXCEPTION")
        log(traceback.format_exc())
        raise
    finally:
        try: _log_f.flush()
        except Exception: pass
        try: _log_f.close()
        except Exception: pass
