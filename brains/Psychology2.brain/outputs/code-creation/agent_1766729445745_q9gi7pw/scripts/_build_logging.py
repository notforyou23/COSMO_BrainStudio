from __future__ import annotations
from pathlib import Path
import json, os, sys, time, platform, shutil, traceback

DEFAULT_TAIL_LINES = int(os.environ.get("BUILD_LOG_TAIL_LINES", "200"))
DEFAULT_LOG_REL = Path("runtime/_build/logs/container_health.jsonl")


def _root_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def log_path(rel: Path | str = DEFAULT_LOG_REL) -> Path:
    p = _root_dir() / Path(rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _tail_lines(text: str, n: int = DEFAULT_TAIL_LINES) -> str:
    if not text:
        return ""
    if n <= 0:
        return ""
    lines = text.splitlines()
    return "\n".join(lines[-n:])


def tail_file(path: str | Path, n: int = DEFAULT_TAIL_LINES, max_bytes: int = 2_000_000) -> str:
    try:
        p = Path(path)
        if not p.is_file():
            return ""
        size = p.stat().st_size
        read_size = min(size, max_bytes)
        with p.open("rb") as f:
            if size > read_size:
                f.seek(-read_size, os.SEEK_END)
            data = f.read()
        try:
            txt = data.decode("utf-8", errors="replace")
        except Exception:
            txt = repr(data[-4000:])
        return _tail_lines(txt, n)
    except Exception:
        return ""


def env_stats(extra_paths: list[str | Path] | None = None) -> dict:
    stats: dict = {}
    stats["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    stats["cwd"] = os.getcwd()
    stats["python"] = {"executable": sys.executable, "version": sys.version.split()[0]}
    stats["platform"] = {"system": platform.system(), "release": platform.release(), "machine": platform.machine()}
    try:
        u = platform.uname()
        stats["uname"] = {"node": u.node, "version": u.version}
    except Exception:
        pass
    try:
        du = shutil.disk_usage(str(_root_dir()))
        stats["disk_root"] = {"total": du.total, "used": du.used, "free": du.free}
    except Exception:
        pass
    try:
        import resource  # type: ignore
        ru = resource.getrusage(resource.RUSAGE_SELF)
        stats["resource"] = {"maxrss_kb": int(getattr(ru, "ru_maxrss", 0) or 0)}
    except Exception:
        pass
    try:
        meminfo = {}
        for pth in ("/proc/meminfo",):
            if os.path.exists(pth):
                with open(pth, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if line.startswith(("MemTotal:", "MemAvailable:", "SwapTotal:", "SwapFree:")):
                            k, v = line.split(":", 1)
                            meminfo[k.strip()] = v.strip()
                break
        if meminfo:
            stats["meminfo"] = meminfo
    except Exception:
        pass
    keep = ("CI", "GITHUB_ACTIONS", "GITHUB_RUN_ID", "GITHUB_SHA", "BUILD_ID", "RUNNER_OS", "HOSTNAME", "USER")
    stats["env"] = {k: os.environ.get(k) for k in keep if k in os.environ}
    if extra_paths:
        paths_stats = {}
        for ep in extra_paths:
            try:
                p = Path(ep)
                if p.exists():
                    st = p.stat()
                    paths_stats[str(p)] = {"size": st.st_size, "mtime": st.st_mtime, "is_file": p.is_file()}
                else:
                    paths_stats[str(p)] = {"exists": False}
            except Exception:
                paths_stats[str(ep)] = {"error": "stat_failed"}
        stats["paths"] = paths_stats
    return stats


def emit_jsonl(record: dict, rel_path: Path | str = DEFAULT_LOG_REL) -> Path:
    p = log_path(rel_path)
    line = json.dumps(record, ensure_ascii=False, sort_keys=False)
    with p.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    return p


def log_failure(
    *,
    stage: str,
    step: str,
    error: str,
    stdout: str | None = None,
    stderr: str | None = None,
    stdout_path: str | Path | None = None,
    stderr_path: str | Path | None = None,
    tail_lines: int = DEFAULT_TAIL_LINES,
    rel_path: Path | str = DEFAULT_LOG_REL,
    extra: dict | None = None,
) -> Path:
    out_tail = _tail_lines(stdout or "", tail_lines)
    err_tail = _tail_lines(stderr or "", tail_lines)
    if stdout_path:
        out_tail = out_tail or tail_file(stdout_path, tail_lines)
    if stderr_path:
        err_tail = err_tail or tail_file(stderr_path, tail_lines)
    rec = {
        "type": "failure",
        "stage": stage,
        "step": step,
        "error": error,
        "stdout_tail": out_tail,
        "stderr_tail": err_tail,
        "env_stats": env_stats(extra_paths=[p for p in (stdout_path, stderr_path) if p]),
    }
    if extra:
        rec["extra"] = extra
    return emit_jsonl(rec, rel_path)


def log_event(
    *,
    event: str,
    stage: str,
    step: str,
    status: str = "info",
    message: str | None = None,
    rel_path: Path | str = DEFAULT_LOG_REL,
    extra: dict | None = None,
) -> Path:
    rec = {"type": "event", "event": event, "stage": stage, "step": step, "status": status, "env_stats": env_stats()}
    if message:
        rec["message"] = message
    if extra:
        rec["extra"] = extra
    return emit_jsonl(rec, rel_path)


def exc_to_str(exc: BaseException) -> str:
    try:
        return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).strip()
    except Exception:
        return f"{type(exc).__name__}: {exc}"
