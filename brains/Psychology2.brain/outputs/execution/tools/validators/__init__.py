"""tools.validators

Package initializer for validator scripts.

Provides small, dependency-light helpers for consistent logging behavior and a
stable location for shared utilities (e.g., preflight checks) across validators.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
import time
from typing import Any, Dict, Optional, Sequence, Tuple
def _now_iso() -> str:
    t = time.time()
    sec = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t))
    ms = int((t - int(t)) * 1000)
    return f"{sec}.{ms:03d}Z"
def _coerce_run_id(run_id: Optional[str] = None) -> str:
    run_id = run_id or os.environ.get("RUN_ID") or os.environ.get("BUILD_RUN_ID")
    if run_id:
        return str(run_id)
    # Stable-enough within a single process; scripts may set RUN_ID for stability across steps.
    return str(int(time.time() * 1000))
def ensure_logs_dir(
    root: str | Path = "_build",
    run_id: Optional[str] = None,
    logs_subdir: str = "logs",
) -> Path:
    rid = _coerce_run_id(run_id)
    root = Path(root)
    logs_dir = root / rid / logs_subdir
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir
@dataclass(frozen=True)
class GateLogger:
    logs_dir: Path
    name: str = "validator"
    stream: str = "diagnostics.jsonl"

    @property
    def path(self) -> Path:
        return self.logs_dir / self.stream

    def emit(self, event: str, **fields: Any) -> None:
        rec: Dict[str, Any] = {
            "ts": _now_iso(),
            "event": event,
            "name": self.name,
            **fields,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, sort_keys=True, ensure_ascii=False) + "\n")

    def emit_exception(self, event: str, exc: BaseException, **fields: Any) -> None:
        self.emit(
            event,
            error_type=type(exc).__name__,
            error=str(exc),
            **fields,
        )
def get_logger(
    *,
    root: str | Path = "_build",
    run_id: Optional[str] = None,
    name: str = "validator",
    stream: str = "diagnostics.jsonl",
) -> GateLogger:
    return GateLogger(ensure_logs_dir(root=root, run_id=run_id), name=name, stream=stream)
def log_kv_file(
    logger: GateLogger,
    filename: str,
    data: Dict[str, Any],
    *,
    mode: str = "w",
) -> Path:
    path = logger.logs_dir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, mode, encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)
        f.write("\n")
    return path
def safe_glob(base: str | Path, pattern: str) -> Tuple[str, Sequence[str]]:
    base_p = Path(base)
    try:
        matches = sorted(str(p) for p in base_p.glob(pattern))
        return (str(base_p), matches)
    except Exception as e:
        return (str(base_p), [f"<glob_error:{type(e).__name__}:{e}>"])
# Optional shared preflight module; validators can import it directly, but we also
# re-export if present for convenience.
try:  # pragma: no cover
    from .preflight import run_preflight, PreflightResult  # type: ignore
except Exception:  # pragma: no cover
    run_preflight = None  # type: ignore

    class PreflightResult:  # type: ignore
        pass
__all__ = [
    "GateLogger",
    "PreflightResult",
    "ensure_logs_dir",
    "get_logger",
    "log_kv_file",
    "run_preflight",
    "safe_glob",
]
