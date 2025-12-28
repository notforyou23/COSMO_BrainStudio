#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, platform, subprocess, sys, time, traceback
from pathlib import Path
try:
    from importlib.metadata import version as pkg_version, PackageNotFoundError
except Exception:  # pragma: no cover
    pkg_version = None
    class PackageNotFoundError(Exception): ...
ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "run_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
def _now_id() -> str:
    return time.strftime("%Y%m%d_%H%M%S")
def _pkg_ver(name: str):
    if not pkg_version:
        return None
    try:
        return pkg_version(name)
    except PackageNotFoundError:
        return None
    except Exception:
        return None
def collect_versions() -> dict:
    pkgs = ["pip","setuptools","wheel","numpy","pandas","scipy","pydantic","jsonschema","pytest"]
    return {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python": sys.version.replace("\n"," "),
        "executable": sys.executable,
        "platform": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
        "cwd": str(Path.cwd()),
        "packages": {p: _pkg_ver(p) for p in pkgs},
    }
def smoke_test() -> dict:
    details = {"ok": True, "checks": []}
    def check(name, fn):
        t0 = time.time()
        try:
            fn()
            details["checks"].append({"name": name, "ok": True, "ms": int((time.time()-t0)*1000)})
        except Exception as e:
            details["ok"] = False
            details["checks"].append({"name": name, "ok": False, "ms": int((time.time()-t0)*1000), "error": repr(e)})
    check("basic_imports", lambda: (__import__("json"), __import__("pathlib"), __import__("subprocess")))
    check("tmp_write", lambda: (LOG_DIR / ".smoke_tmp").write_text("ok", encoding="utf-8"))
    check("tmp_cleanup", lambda: (LOG_DIR / ".smoke_tmp").unlink(missing_ok=True))
    check("python_exec", lambda: subprocess.run([sys.executable, "-c", "import sys; print(sys.version_info[0])"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True))
    return details
def _as_cmd(item):
    if item is None:
        return None
    if isinstance(item, str):
        return item
    if isinstance(item, list):
        return [str(x) for x in item]
    if isinstance(item, dict) and "cmd" in item:
        return _as_cmd(item["cmd"])
    return None
def _iter_commands(script: dict):
    for key in ("smoke_test_commands","validators","validator_commands","meta_analysis","meta_analysis_commands","commands","steps"):
        val = script.get(key)
        if not val:
            continue
        if isinstance(val, dict):
            val = val.get("commands") or val.get("steps")
        if isinstance(val, (str, list, dict)):
            val = [val]
        for it in (val or []):
            cmd = _as_cmd(it)
            if cmd:
                yield {"group": key, "cmd": cmd}
def run_command(cmd, log_fp, env=None) -> dict:
    t0 = time.time()
    p = subprocess.run(cmd, shell=isinstance(cmd, str), cwd=str(ROOT), env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out = (p.stdout or "")
    err = (p.stderr or "")
    log_fp.write(f"$ {cmd}\n")
    if out:
        log_fp.write(out if out.endswith("\n") else out + "\n")
    if err:
        log_fp.write(err if err.endswith("\n") else err + "\n")
    return {"cmd": cmd, "returncode": p.returncode, "seconds": round(time.time()-t0, 3),
            "stdout_bytes": len(out.encode("utf-8","ignore")), "stderr_bytes": len(err.encode("utf-8","ignore"))}
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="JSON-script pipeline runner with smoke-test and reproducibility logging.")
    ap.add_argument("script", help="Path to JSON pipeline script")
    ap.add_argument("--run-id", default=_now_id(), help="Override run id (default: timestamp)")
    args = ap.parse_args(argv)
    run_id = args.run_id
    script_path = (Path(args.script).expanduser().resolve() if args.script else None)
    raw_log_path = LOG_DIR / f"run_{run_id}.log"
    json_log_path = LOG_DIR / f"run_{run_id}.json"
    record = {"run_id": run_id, "script_path": str(script_path) if script_path else None,
              "root": str(ROOT), "versions": collect_versions(), "smoke_test": None,
              "commands": [], "ok": False, "error": None}
    try:
        if not script_path or not script_path.is_file():
            raise FileNotFoundError(f"Script not found: {script_path}")
        script = json.loads(script_path.read_text(encoding="utf-8"))
        record["smoke_test"] = smoke_test()
        with raw_log_path.open("w", encoding="utf-8") as lf:
            lf.write(f"RUN_ID={run_id}\nSCRIPT={script_path}\nROOT={ROOT}\n\n")
            if not record["smoke_test"]["ok"]:
                lf.write("SMOKE_TEST_FAILED\n")
                record["ok"] = False
            else:
                for spec in _iter_commands(script):
                    res = run_command(spec["cmd"], lf, env=os.environ.copy())
                    res["group"] = spec.get("group")
                    record["commands"].append(res)
                    if res["returncode"] != 0:
                        record["ok"] = False
                        break
                else:
                    record["ok"] = True
    except Exception as e:
        record["ok"] = False
        record["error"] = {"type": type(e).__name__, "message": str(e), "traceback": traceback.format_exc()}
    json_log_path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    return 0 if record.get("ok") else 2
if __name__ == "__main__":
    raise SystemExit(main())
