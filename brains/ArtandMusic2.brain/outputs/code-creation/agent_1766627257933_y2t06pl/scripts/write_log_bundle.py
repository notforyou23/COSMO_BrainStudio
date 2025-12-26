from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import socket
import sys
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple, Union


PathLike = Union[str, os.PathLike]


def utc_timestamp() -> str:
    """UTC timestamp safe for filenames."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S-%fZ")


def _can_write_dir(p: Path) -> bool:
    try:
        p.mkdir(parents=True, exist_ok=True)
        test = p / ".write_test"
        test.write_text("ok", encoding="utf-8")
        test.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def resolve_output_root(
    env: Optional[Mapping[str, str]] = None,
    candidates: Optional[Sequence[PathLike]] = None,
    fallback_rel: str = "outputs",
) -> Path:
    """Resolve a canonical output root directory with robust fallbacks.

    Priority:
      1) env OUT_DIR / OUTPUT_DIR / OUTPUTS_DIR (first that works)
      2) candidate directories (defaults: /out, /outputs)
      3) ./<fallback_rel>
    """
    env = dict(os.environ) if env is None else dict(env)
    env_keys = ("OUT_DIR", "OUTPUT_DIR", "OUTPUTS_DIR")
    for k in env_keys:
        v = env.get(k)
        if v:
            p = Path(v)
            if _can_write_dir(p):
                return p

    if candidates is None:
        candidates = ("/out", "/outputs")
    for c in candidates:
        p = Path(c)
        if _can_write_dir(p):
            return p

    p = Path.cwd() / fallback_rel
    if _can_write_dir(p):
        return p

    # Last resort: temp-like in cwd
    p = Path.cwd() / ".out"
    p.mkdir(parents=True, exist_ok=True)
    return p


def create_bundle_dir(
    root: Optional[PathLike] = None,
    name: str = "smoke",
    ts: Optional[str] = None,
) -> Path:
    """Create and return a timestamped bundle directory under the output root."""
    root_path = Path(root) if root is not None else resolve_output_root()
    stamp = ts or utc_timestamp()
    safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in name).strip("_") or "bundle"
    bundle = root_path / f"{stamp}_{safe_name}"
    bundle.mkdir(parents=True, exist_ok=False)
    return bundle


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


@dataclass(frozen=True)
class RunResult:
    cmd: Union[str, Sequence[str]]
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_ms: Optional[int] = None
    cwd: Optional[str] = None


def _cmd_to_display(cmd: Union[str, Sequence[str]]) -> str:
    if isinstance(cmd, str):
        return cmd
    return " ".join(str(x) for x in cmd)


def write_run_bundle(
    bundle_dir: Path,
    result: RunResult,
    extra_meta: Optional[Mapping[str, Any]] = None,
    stdout_name: str = "stdout.txt",
    stderr_name: str = "stderr.txt",
    meta_name: str = "meta.json",
) -> Dict[str, Any]:
    """Write stdout/stderr and structured metadata into an existing bundle directory."""
    bundle_dir.mkdir(parents=True, exist_ok=True)

    write_text(bundle_dir / stdout_name, result.stdout or "")
    write_text(bundle_dir / stderr_name, result.stderr or "")

    meta: Dict[str, Any] = {
        "timestamp_utc": utc_timestamp(),
        "host": {"hostname": socket.gethostname()},
        "python": {"version": sys.version, "executable": sys.executable},
        "command": {
            "raw": result.cmd,
            "display": _cmd_to_display(result.cmd),
            "cwd": result.cwd or os.getcwd(),
        },
        "result": {
            "exit_code": int(result.exit_code),
            "duration_ms": result.duration_ms,
            "stdout_path": stdout_name,
            "stderr_path": stderr_name,
        },
    }
    if extra_meta:
        meta["extra"] = dict(extra_meta)

    write_json(bundle_dir / meta_name, meta)
    return meta
