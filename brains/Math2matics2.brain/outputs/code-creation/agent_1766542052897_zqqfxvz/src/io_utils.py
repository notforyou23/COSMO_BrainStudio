"""I/O utilities for the evidence-pack pipeline.

Provides:
- Directory management helpers
- Deterministic JSON read/write
- Structured JSONL logging
- Reproducible run timestamp + metadata capture (supports SOURCE_DATE_EPOCH)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional
import json
import os
import platform
import sys
import hashlib
def ensure_dir(path: Path) -> Path:
    """Create *path* as a directory (parents=True) and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path) -> Any:
    """Read JSON from *path* using UTF-8."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any, *, indent: int = 2, sort_keys: bool = True) -> None:
    """Write JSON to *path* deterministically (sorted keys, LF newlines)."""
    text = json.dumps(obj, indent=indent, sort_keys=sort_keys, ensure_ascii=False)
    path.write_text(text + "\n", encoding="utf-8")
def _env_int(name: str) -> Optional[int]:
    v = os.environ.get(name)
    if v is None or v == "":
        return None
    try:
        return int(v)
    except ValueError:
        return None


def run_timestamp() -> str:
    """Return a reproducible UTC timestamp string.

    Uses (in order): EVIDENCE_PACK_TIMESTAMP, SOURCE_DATE_EPOCH, else current time.
    Format: YYYY-MM-DDTHH:MM:SSZ
    """
    fixed = os.environ.get("EVIDENCE_PACK_TIMESTAMP")
    if fixed:
        return fixed
    sde = _env_int("SOURCE_DATE_EPOCH")
    if sde is not None:
        dt = datetime.fromtimestamp(sde, tz=timezone.utc)
    else:
        dt = datetime.now(tz=timezone.utc)
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")
@dataclass(frozen=True)
class RunMeta:
    """Minimal run metadata captured for evidence packs."""

    run_id: str
    started_at: str
    seed: int
    python: str
    platform: str
    cwd: str

    def as_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "seed": self.seed,
            "python": self.python,
            "platform": self.platform,
            "cwd": self.cwd,
        }


def make_run_meta(*, seed: int = 0, started_at: Optional[str] = None) -> RunMeta:
    """Create reproducible run metadata.

    run_id is a stable short hash of (started_at, seed, cwd).
    """
    ts = started_at or run_timestamp()
    cwd = str(Path.cwd())
    h = hashlib.sha256(f"{ts}|{seed}|{cwd}".encode("utf-8")).hexdigest()[:12]
    return RunMeta(
        run_id=h,
        started_at=ts,
        seed=int(seed),
        python=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        platform=platform.platform(),
        cwd=cwd,
    )
def make_jsonl_logger(log_path: Path, *, meta: Optional[RunMeta] = None) -> Callable[..., None]:
    """Return a structured logger writing one JSON object per line.

    Each event includes: ts, level, event, and optional meta.run_id.
    The returned callable signature is: log(event, level="INFO", **fields).
    """
    ensure_dir(log_path.parent)
    fh = log_path.open("a", encoding="utf-8", newline="\n")

    def log(event: str, *, level: str = "INFO", **fields: Any) -> None:
        rec: Dict[str, Any] = {"ts": run_timestamp(), "level": level, "event": event}
        if meta is not None:
            rec["run_id"] = meta.run_id
        if fields:
            rec.update(fields)
        fh.write(json.dumps(rec, sort_keys=True, ensure_ascii=False) + "\n")
        fh.flush()

    return log
