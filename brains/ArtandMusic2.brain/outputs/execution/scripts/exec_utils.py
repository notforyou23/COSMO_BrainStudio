from __future__ import annotations
import os, sys, json, time, shlex, threading, subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Union, Dict, Any

TextOrPath = Union[str, Path]
Cmd = Union[str, Sequence[str]]

def _iso_utc(ts: Optional[float] = None) -> str:
    ts = time.time() if ts is None else ts
    ms = int(round((ts - int(ts)) * 1000.0))
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(ts)) + f".{ms:03d}Z"

def _ensure_dir(p: TextOrPath) -> Path:
    p = Path(p)
    p.mkdir(parents=True, exist_ok=True)
    return p

def canonical_exec_log_dir(root: Optional[TextOrPath] = None) -> Path:
    if root is None:
        root = Path.cwd()
    return _ensure_dir(Path(root) / "outputs" / "qa" / "exec_logs")

def _cmd_display(cmd: Cmd) -> str:
    if isinstance(cmd, (list, tuple)):
        return " ".join(shlex.quote(str(x)) for x in cmd)
    return cmd

@dataclass
class ExecResult:
    returncode: int
    attempt: int
    start_utc: str
    end_utc: str
    duration_s: float
    cmd: str
    stdout_path: Path
    stderr_path: Path
    meta_path: Path
    cwd: Optional[str] = None

def _write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
def _pump_stream(
    stream, out_fh, tee_fh, prefix: str, lock: threading.Lock, add_timestamps: bool
) -> None:
    try:
        for raw in iter(stream.readline, b""):
            if not raw:
                break
            try:
                txt = raw.decode("utf-8", errors="replace")
            except Exception:
                txt = str(raw)
            if add_timestamps:
                line = f"{_iso_utc()} {prefix}{txt}"
            else:
                line = f"{prefix}{txt}" if prefix else txt
            out_fh.write(line)
            out_fh.flush()
            if tee_fh is not None:
                with lock:
                    tee_fh.write(line)
                    tee_fh.flush()
    finally:
        try:
            stream.close()
        except Exception:
            pass

def run_exec(
    cmd: Cmd,
    *,
    log_dir: Optional[TextOrPath] = None,
    name: str = "exec",
    attempt: int = 1,
    cwd: Optional[TextOrPath] = None,
    env: Optional[Dict[str, str]] = None,
    timeout_s: Optional[float] = None,
    add_timestamps: bool = True,
    stream_to_console: bool = True,
) -> ExecResult:
    log_dir_p = canonical_exec_log_dir() if log_dir is None else _ensure_dir(log_dir)
    start_ts = time.time()
    start_utc = _iso_utc(start_ts)
    base = f"{start_utc.replace(':','-')}_{name}_attempt{attempt}"
    stdout_path = log_dir_p / f"{base}.stdout.log"
    stderr_path = log_dir_p / f"{base}.stderr.log"
    meta_path = log_dir_p / f"{base}.meta.json"

    disp = _cmd_display(cmd)
    meta: Dict[str, Any] = {
        "name": name,
        "attempt": attempt,
        "start_utc": start_utc,
        "cmd": disp,
        "cwd": str(cwd) if cwd is not None else None,
        "python": sys.executable,
        "pid": os.getpid(),
    }
    _write_json(meta_path, meta)

    out_console = sys.stdout if stream_to_console else open(os.devnull, "w", encoding="utf-8")
    err_console = sys.stderr if stream_to_console else open(os.devnull, "w", encoding="utf-8")
    lock = threading.Lock()
    rc = 1
    try:
        with open(stdout_path, "w", encoding="utf-8") as out_f, open(stderr_path, "w", encoding="utf-8") as err_f:
            p = subprocess.Popen(
                cmd,
                cwd=str(cwd) if cwd is not None else None,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
            )
            t_out = threading.Thread(
                target=_pump_stream,
                args=(p.stdout, out_f, out_console, "", lock, add_timestamps),
                daemon=True,
            )
            t_err = threading.Thread(
                target=_pump_stream,
                args=(p.stderr, err_f, err_console, "ERR ", lock, add_timestamps),
                daemon=True,
            )
            t_out.start(); t_err.start()
            try:
                rc = p.wait(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                meta["timeout_s"] = timeout_s
                try:
                    p.kill()
                except Exception:
                    pass
                rc = 124
            t_out.join(timeout=5); t_err.join(timeout=5)
    finally:
        if not stream_to_console:
            try:
                out_console.close()
            except Exception:
                pass
            try:
                err_console.close()
            except Exception:
                pass

    end_ts = time.time()
    end_utc = _iso_utc(end_ts)
    meta.update(
        {
            "end_utc": end_utc,
            "duration_s": round(end_ts - start_ts, 6),
            "returncode": int(rc),
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "meta_path": str(meta_path),
        }
    )
    _write_json(meta_path, meta)
    return ExecResult(
        returncode=int(rc),
        attempt=int(attempt),
        start_utc=start_utc,
        end_utc=end_utc,
        duration_s=float(meta["duration_s"]),
        cmd=disp,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        meta_path=meta_path,
        cwd=str(cwd) if cwd is not None else None,
    )
