"""tools.support.run_id

Helper to resolve or generate a stable run_id so all tools can route logs to:
  _build/<run_id>/logs/

Resolution order:
  1) explicit argument (preferred)
  2) environment variables
  3) persisted state file under _build/.run_id
  4) generated id (then persisted)
"""

from __future__ import annotations

from pathlib import Path
import os
import secrets
import time
from typing import Iterable, Optional, Tuple
DEFAULT_ENV_KEYS = (
    "RUN_ID",
    "COSMO_RUN_ID",
    "BUILD_RUN_ID",
    "CI_RUN_ID",
)
def _clean_run_id(value: str) -> str:
    v = (value or "").strip()
    if not v:
        return ""
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-")
    return "".join(ch for ch in v if ch in allowed)
def _state_file(base_dir: Path) -> Path:
    return base_dir.joinpath("_build", ".run_id")
def _read_state(path: Path) -> str:
    try:
        txt = path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""
    return _clean_run_id(txt)
def _write_state_atomic(path: Path, run_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}.{secrets.token_hex(4)}")
    tmp.write_text(run_id + "\n", encoding="utf-8")
    try:
        os.replace(tmp, path)
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass
def generate_run_id(prefix: str = "run") -> str:
    ts = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    return _clean_run_id(f"{prefix}_{ts}_{os.getpid()}_{secrets.token_hex(6)}")
def resolve_run_id(
    preferred: Optional[str] = None,
    *,
    base_dir: Optional[Path] = None,
    env_keys: Iterable[str] = DEFAULT_ENV_KEYS,
    persist: bool = True,
) -> str:
    """Resolve a stable run_id for this workspace.

    base_dir is the repository/workspace root; defaults to current working directory.
    """
    base = Path(base_dir) if base_dir is not None else Path.cwd()

    rid = _clean_run_id(preferred or "")
    if rid:
        if persist:
            _write_state_atomic(_state_file(base), rid)
        return rid

    for k in env_keys:
        rid = _clean_run_id(os.environ.get(str(k), ""))
        if rid:
            if persist:
                _write_state_atomic(_state_file(base), rid)
            return rid

    state = _state_file(base)
    rid = _read_state(state)
    if rid:
        return rid

    rid = generate_run_id()
    if persist:
        _write_state_atomic(state, rid)
    return rid
def build_and_logs_dirs(
    run_id: Optional[str] = None, *, base_dir: Optional[Path] = None, ensure: bool = True
) -> Tuple[Path, Path]:
    """Return (_build/<run_id>, _build/<run_id>/logs)."""
    base = Path(base_dir) if base_dir is not None else Path.cwd()
    rid = resolve_run_id(run_id, base_dir=base)
    build_dir = base.joinpath("_build", rid)
    logs_dir = build_dir.joinpath("logs")
    if ensure:
        logs_dir.mkdir(parents=True, exist_ok=True)
    return build_dir, logs_dir
if __name__ == "__main__":
    rid = resolve_run_id()
    print(rid)
