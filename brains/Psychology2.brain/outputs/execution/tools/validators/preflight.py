"""tools.validators.preflight

Reusable preflight validation utilities to capture environment/filesystem
diagnostics and persist them under _build/<run_id>/logs/ before exit.
""""

from __future__ import annotations

import glob
import json
import os
import platform
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def resolve_run_id(explicit: Optional[str] = None) -> str:
    rid = (explicit or os.environ.get("RUN_ID") or os.environ.get("BUILD_RUN_ID") or "").strip()
    if rid:
        return rid
    for k in ("GITHUB_RUN_ID", "CI_PIPELINE_ID", "BUILD_ID"):
        v = (os.environ.get(k) or "").strip()
        if v:
            return v
    return time.strftime("%Y%m%d_%H%M%S")


def logs_dir(run_id: str, root: Optional[Path] = None) -> Path:
    root = root or Path.cwd()
    d = root / "_build" / run_id / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _safe_read_text(p: Path, limit: int = 200_000) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")[:limit]
    except Exception as e:
        return f"<unreadable:{type(e).__name__}:{e}>"


def _umask_value() -> Optional[int]:
    try:
        current = os.umask(0)
        os.umask(current)
        return current
    except Exception:
        return None


def _mounts() -> Dict[str, Any]:
    proc = Path("/proc/mounts")
    if proc.exists():
        txt = _safe_read_text(proc, limit=500_000)
        lines = [ln for ln in txt.splitlines() if ln.strip()]
        return {"source": "/proc/mounts", "count": len(lines), "lines": lines[:300]}
    try:
        cp = subprocess.run(["mount"], capture_output=True, text=True, check=False)
        out = (cp.stdout or "") + ("\n" + cp.stderr if cp.stderr else "")
        lines = [ln for ln in out.splitlines() if ln.strip()]
        return {"source": "mount", "rc": cp.returncode, "count": len(lines), "lines": lines[:300]}
    except Exception as e:
        return {"source": "mount", "error": f"{type(e).__name__}:{e}"}


def _path_probe(p: Path) -> Dict[str, Any]:
    info: Dict[str, Any] = {"path": str(p)}
    try:
        st = p.lstat()
        info.update(
            exists=True,
            is_dir=p.is_dir(),
            is_file=p.is_file(),
            is_symlink=p.is_symlink(),
            size=getattr(st, "st_size", None),
            mode=oct(getattr(st, "st_mode", 0)),
            uid=getattr(st, "st_uid", None),
            gid=getattr(st, "st_gid", None),
        )
    except FileNotFoundError:
        info.update(exists=False)
        return info
    except Exception as e:
        info.update(exists=None, error=f"{type(e).__name__}:{e}")
        return info

    def _acc(flag: int) -> Optional[bool]:
        try:
            return os.access(str(p), flag)
        except Exception:
            return None

    info["readable"] = _acc(os.R_OK)
    info["writable"] = _acc(os.W_OK)
    info["executable"] = _acc(os.X_OK)
    return info


def _glob_probe(pattern: str, cwd: Optional[Path] = None, limit: int = 200) -> Dict[str, Any]:
    cwd = cwd or Path.cwd()
    try:
        results = glob.glob(pattern, recursive=True)
        results = [str(Path(r)) for r in results]
        return {"pattern": pattern, "cwd": str(cwd), "count": len(results), "results": results[:limit]}
    except Exception as e:
        return {"pattern": pattern, "cwd": str(cwd), "error": f"{type(e).__name__}:{e}"}


def collect_diagnostics(
    *,
    run_id: str,
    expected_paths: Optional[Iterable[str]] = None,
    glob_patterns: Optional[Iterable[str]] = None,
    cwd: Optional[Path] = None,
) -> Dict[str, Any]:
    cwd = cwd or Path.cwd()
    expected_paths = list(expected_paths or [])
    glob_patterns = list(glob_patterns or [])
    diag: Dict[str, Any] = {
        "run_id": run_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "cwd": str(cwd),
        "argv": list(sys.argv),
        "python": {"executable": sys.executable, "version": sys.version},
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "platform": platform.platform(),
        },
        "host": {"hostname": socket.gethostname()},
        "ids": {
            "uid": getattr(os, "getuid", lambda: None)(),
            "gid": getattr(os, "getgid", lambda: None)(),
            "euid": getattr(os, "geteuid", lambda: None)(),
            "egid": getattr(os, "getegid", lambda: None)(),
        },
        "umask": _umask_value(),
        "env": {k: os.environ.get(k) for k in sorted(os.environ) if k.startswith(("CI", "GITHUB_", "RUN_", "BUILD_", "PWD", "HOME", "USER"))},
        "mounts": _mounts(),
        "paths": [],
        "globs": [],
    }

    for s in expected_paths:
        p = Path(s)
        if not p.is_absolute():
            p = cwd / p
        diag["paths"].append(_path_probe(p))

    for pat in glob_patterns:
        diag["globs"].append(_glob_probe(pat, cwd=cwd))

    return diag


def write_diagnostics(diag: Dict[str, Any], *, log_dir: Path, prefix: str = "preflight") -> Tuple[Path, Path]:
    log_dir.mkdir(parents=True, exist_ok=True)
    jpath = log_dir / f"{prefix}.json"
    tpath = log_dir / f"{prefix}.txt"
    jpath.write_text(json.dumps(diag, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    lines: List[str] = []
    lines.append(f"run_id={diag.get('run_id')} ts={diag.get('timestamp')}")
    lines.append(f"cwd={diag.get('cwd')}")
    ids = diag.get("ids") or {}
    lines.append(f"uid/gid={ids.get('uid')}/{ids.get('gid')} euid/egid={ids.get('euid')}/{ids.get('egid')} umask={diag.get('umask')}")
    lines.append(f"python={diag.get('python', {}).get('executable')}")
    lines.append(f"python_version={diag.get('python', {}).get('version', '').splitlines()[0] if diag.get('python') else ''}")
    lines.append("\n[paths]")
    for p in diag.get("paths", []):
        lines.append(f"- {p.get('path')} exists={p.get('exists')} dir={p.get('is_dir')} file={p.get('is_file')} r/w/x={p.get('readable')}/{p.get('writable')}/{p.get('executable')} err={p.get('error')}")
    lines.append("\n[globs]")
    for g in diag.get("globs", []):
        if "error" in g:
            lines.append(f"- {g.get('pattern')} ERROR {g.get('error')}")
        else:
            lines.append(f"- {g.get('pattern')} count={g.get('count')} sample={g.get('results', [])[:10]}")
    tpath.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return jpath, tpath


def run_preflight(
    *,
    run_id: Optional[str] = None,
    root: Optional[Path] = None,
    expected_paths: Optional[Iterable[str]] = None,
    glob_patterns: Optional[Iterable[str]] = None,
    prefix: str = "preflight",
) -> Dict[str, Any]:
    rid = resolve_run_id(run_id)
    root = root or Path.cwd()
    ld = logs_dir(rid, root=root)
    diag = collect_diagnostics(run_id=rid, expected_paths=expected_paths, glob_patterns=glob_patterns, cwd=root)
    write_diagnostics(diag, log_dir=ld, prefix=prefix)
    return diag
