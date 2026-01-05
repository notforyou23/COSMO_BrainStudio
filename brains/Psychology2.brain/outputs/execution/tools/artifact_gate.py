#!/usr/bin/env python3
from __future__ import annotations

import argparse
import atexit
import glob
import json
import os
import platform
import stat
import sys
import time
import traceback
from pathlib import Path


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z"


def _safe_umask_probe():
    try:
        old = os.umask(0)
        os.umask(old)
        return old
    except Exception:
        return None


def _read_text(path: Path, limit: int = 200_000) -> str | None:
    try:
        data = path.read_text(encoding="utf-8", errors="replace")
        return data[:limit]
    except Exception:
        try:
            b = path.read_bytes()
            return b[:limit].decode("utf-8", errors="replace")
        except Exception:
            return None


def _path_probe(p: Path) -> dict:
    d = {"path": str(p)}
    try:
        d["exists"] = p.exists()
        d["is_file"] = p.is_file()
        d["is_dir"] = p.is_dir()
    except Exception as e:
        d["error"] = f"exists_probe:{type(e).__name__}:{e}"
        return d
    if not d.get("exists"):
        return d
    try:
        st = p.stat()
        d["mode_octal"] = oct(st.st_mode & 0o7777)
        d["uid"] = getattr(st, "st_uid", None)
        d["gid"] = getattr(st, "st_gid", None)
        d["size"] = getattr(st, "st_size", None)
    except Exception as e:
        d["stat_error"] = f"{type(e).__name__}:{e}"
    try:
        d["readable"] = os.access(p, os.R_OK)
        d["writable"] = os.access(p, os.W_OK)
        d["executable"] = os.access(p, os.X_OK)
    except Exception as e:
        d["access_error"] = f"{type(e).__name__}:{e}"
    return d


def _mounts_snapshot() -> dict:
    out = {"source": None, "data": None, "error": None}
    candidates = [Path("/proc/mounts"), Path("/etc/mtab")]
    for c in candidates:
        if c.exists():
            out["source"] = str(c)
            out["data"] = _read_text(c)
            return out
    out["error"] = "no_mount_table_found"
    return out


class _Logger:
    def __init__(self, log_dir: Path, run_id: str):
        self.log_dir = log_dir
        self.run_id = run_id
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.jsonl_path = self.log_dir / "artifact_gate.preflight.jsonl"
        self.txt_path = self.log_dir / "artifact_gate.preflight.txt"
        self._jsonl = open(self.jsonl_path, "a", encoding="utf-8")
        self._txt = open(self.txt_path, "a", encoding="utf-8")
        atexit.register(self.close)

    def close(self):
        for f in (getattr(self, "_jsonl", None), getattr(self, "_txt", None)):
            try:
                if f:
                    f.flush()
                    f.close()
            except Exception:
                pass

    def event(self, kind: str, payload: dict):
        rec = {"ts": _now(), "run_id": self.run_id, "kind": kind, **payload}
        try:
            self._jsonl.write(json.dumps(rec, sort_keys=True) + "\n")
            self._jsonl.flush()
        except Exception:
            pass
        try:
            self._txt.write(f"[{rec['ts']}] {kind}: {json.dumps(payload, sort_keys=True)}\n")
            self._txt.flush()
        except Exception:
            pass


def _resolve_run_id(cli_run_id: str | None) -> str:
    for k in ("RUN_ID", "run_id", "GITHUB_RUN_ID", "BUILD_ID", "CI_RUN_ID"):
        v = os.environ.get(k)
        if v:
            return str(v)
    if cli_run_id:
        return str(cli_run_id)
    return time.strftime("%Y%m%d_%H%M%S", time.gmtime())


def _preflight(logger: _Logger, expected_paths: list[str], glob_patterns: list[str], workdir: str | None):
    try:
        uid = os.getuid()
        gid = os.getgid()
    except Exception:
        uid = gid = None

    env_subset_keys = [
        "PWD", "HOME", "USER", "LOGNAME", "SHELL", "PATH",
        "CI", "GITHUB_ACTIONS", "GITHUB_WORKSPACE", "RUN_ID",
        "PYTHONPATH", "VIRTUAL_ENV",
    ]
    env_subset = {k: os.environ.get(k) for k in env_subset_keys if os.environ.get(k) is not None}

    logger.event("context", {
        "argv": sys.argv,
        "python": sys.version.replace("\n", " "),
        "executable": sys.executable,
        "platform": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
        "cwd": os.getcwd(),
        "uid": uid,
        "gid": gid,
        "umask": _safe_umask_probe(),
        "env_subset": env_subset,
    })

    if workdir:
        try:
            Path(workdir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.event("workdir_mkdir_error", {"workdir": workdir, "error": f"{type(e).__name__}:{e}"})
        try:
            os.chdir(workdir)
            logger.event("workdir_set", {"workdir": workdir, "cwd": os.getcwd()})
        except Exception as e:
            logger.event("workdir_chdir_error", {"workdir": workdir, "error": f"{type(e).__name__}:{e}"})

    logger.event("mounts", _mounts_snapshot())

    probes = []
    for p in expected_paths:
        probes.append(_path_probe(Path(p)))
    logger.event("expected_paths", {"probes": probes})

    glob_results = []
    for pat in glob_patterns:
        try:
            matches = sorted(glob.glob(pat, recursive=True))
            glob_results.append({"pattern": pat, "count": len(matches), "matches": matches[:200]})
        except Exception as e:
            glob_results.append({"pattern": pat, "error": f"{type(e).__name__}:{e}"})
    logger.event("glob_results", {"results": glob_results})


def _fail(logger: _Logger, code: int, msg: str, extra: dict | None = None):
    payload = {"code": int(code), "message": msg}
    if extra:
        payload.update(extra)
    logger.event("fatal", payload)
    try:
        logger.event("final_note", {"logs_dir": str(logger.log_dir), "jsonl": str(logger.jsonl_path), "txt": str(logger.txt_path)})
    except Exception:
        pass
    logger.close()
    raise SystemExit(code)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Artifact gate with preflight diagnostics (writes logs before exit).")
    ap.add_argument("--run-id", default=None, help="Run identifier used for routing logs into _build/<run_id>/logs/")
    ap.add_argument("--workdir", default=None, help="Optional working directory to chdir into before validation.")
    ap.add_argument("--expected-path", action="append", default=[], help="Path expected to exist (may be repeated).")
    ap.add_argument("--glob", dest="globs", action="append", default=[], help="Glob patterns to expand and validate (may be repeated).")
    ap.add_argument("--require-glob-nonempty", action="store_true", help="Fail if any provided glob expands to zero matches.")
    ap.add_argument("--repro-failure", action="store_true", help="Reproduce failure mode: require missing _build/<run_id>/artifacts/REQUIRED.ok")
    args = ap.parse_args(argv)

    run_id = _resolve_run_id(args.run_id)
    build_dir = Path("_build") / run_id
    logs_dir = build_dir / "logs"
    logger = _Logger(logs_dir, run_id)

    expected = list(args.expected_path)
    globs = list(args.globs)

    # Default expected build/log structure and common CI mount roots.
    if not expected:
        expected = [str(Path(".")), str(Path("_build")), str(build_dir), str(logs_dir), "/mnt", '/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution']
    if not globs:
        globs = [str(build_dir / "**" / "*")]

    # Ensure logs directory exists early and is writable.
    logger.event("log_dir_probe", {"probe": _path_probe(logs_dir)})
    if not logs_dir.exists():
        try:
            logs_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            _fail(logger, 21, "Unable to create logs directory", {"logs_dir": str(logs_dir), "error": f"{type(e).__name__}:{e}"})
    if not os.access(logs_dir, os.W_OK):
        _fail(logger, 22, "Logs directory is not writable", {"logs_dir": str(logs_dir), "probe": _path_probe(logs_dir)})

    # Preflight snapshot before validation.
    _preflight(logger, expected, globs, args.workdir)

    # Reproduce historical failure mode: missing required marker file under artifacts.
    if args.repro_failure:
        required = build_dir / "artifacts" / "REQUIRED.ok"
        logger.event("repro_failure_check", {"required_path": str(required), "probe": _path_probe(required)})
        if not required.exists():
            _fail(logger, 2, "Repro failure: required artifact marker missing", {"required_path": str(required)})

    # Validate expected paths.
    missing = []
    for p in expected:
        if p and not Path(p).exists():
            missing.append(p)
    if missing:
        _fail(logger, 3, "Expected path(s) missing", {"missing": missing})

    # Validate globs.
    if args.require_glob_nonempty and globs:
        empty = []
        for pat in globs:
            try:
                if len(glob.glob(pat, recursive=True)) == 0:
                    empty.append(pat)
            except Exception as e:
                empty.append(f"{pat} (glob_error:{type(e).__name__}:{e})")
        if empty:
            _fail(logger, 4, "One or more glob patterns produced no matches", {"empty_globs": empty})

    logger.event("ok", {"message": "artifact gate passed", "logs_dir": str(logs_dir)})
    logger.close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except Exception as e:
        # Best-effort: attempt to write a crash log under a resolved run_id.
        try:
            run_id = _resolve_run_id(None)
            logs_dir = Path("_build") / run_id / "logs"
            logs_dir.mkdir(parents=True, exist_ok=True)
            crash = logs_dir / "artifact_gate.crash.txt"
            crash.write_text("UNHANDLED_EXCEPTION\n" + traceback.format_exc(), encoding="utf-8")
        except Exception:
            pass
        raise SystemExit(99) from e
