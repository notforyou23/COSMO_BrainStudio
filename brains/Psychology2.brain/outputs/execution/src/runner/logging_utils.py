from __future__ import annotations

import os
import sys
import io
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, TextIO, Iterable
def utc_now_iso(timespec: str = "seconds") -> str:
    return datetime.now(timezone.utc).isoformat(timespec=timespec).replace("+00:00", "Z")


def format_ts_line(prefix: str, message: str) -> str:
    msg = message.rstrip("\n")
    return f"[{utc_now_iso()}] {prefix}{msg}\n"


def open_text_log(path: Path) -> TextIO:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Line-buffered so each newline flushes promptly; also allow explicit flush.
    return open(path, "a", encoding="utf-8", buffering=1)
class _TeeTextIO(io.TextIOBase):
    def __init__(self, streams: Iterable[TextIO]):
        self._streams = [s for s in streams if s is not None]

    def writable(self) -> bool:
        return True

    def write(self, s: str) -> int:
        n = 0
        for st in self._streams:
            try:
                n = max(n, st.write(s))
            except Exception:
                # Best-effort: never let logging kill the run.
                pass
        self.flush()
        return n

    def flush(self) -> None:
        for st in self._streams:
            try:
                st.flush()
            except Exception:
                pass
@dataclass
class TeeState:
    log_path: Path
    log_fp: TextIO
    stdout_prev: TextIO
    stderr_prev: TextIO
    start_utc_iso: str


class TeeOutput:
    """Context manager that tees stdout/stderr to a single complete run log."""

    def __init__(self, log_path: Path, *, write_banner: bool = True):
        self.log_path = Path(log_path)
        self.write_banner = write_banner
        self._state: Optional[TeeState] = None

    def __enter__(self) -> TeeState:
        log_fp = open_text_log(self.log_path)
        start = utc_now_iso()

        stdout_prev, stderr_prev = sys.stdout, sys.stderr
        sys.stdout = _TeeTextIO([stdout_prev, log_fp])  # type: ignore[assignment]
        sys.stderr = _TeeTextIO([stderr_prev, log_fp])  # type: ignore[assignment]

        self._state = TeeState(
            log_path=self.log_path,
            log_fp=log_fp,
            stdout_prev=stdout_prev,
            stderr_prev=stderr_prev,
            start_utc_iso=start,
        )

        if self.write_banner:
            banner = (
                f"=== RUN START {start} ===\n"
                f"pid={os.getpid()} ppid={os.getppid()} cwd={os.getcwd()}\n"
                f"python={sys.executable}\n"
            )
            try:
                log_fp.write(banner)
                log_fp.flush()
            except Exception:
                pass
        return self._state

    def __exit__(self, exc_type, exc, tb) -> bool:
        state = self._state
        if state is None:
            return False
        try:
            end = utc_now_iso()
            try:
                state.log_fp.write(f"=== RUN END {end} ===\n")
                state.log_fp.flush()
            except Exception:
                pass
        finally:
            sys.stdout = state.stdout_prev  # type: ignore[assignment]
            sys.stderr = state.stderr_prev  # type: ignore[assignment]
            try:
                state.log_fp.flush()
                state.log_fp.close()
            except Exception:
                pass
        return False
def log_event(log_fp: TextIO, event: str, **fields) -> None:
    """Write a single-line JSON event to the run log with UTC timestamp.

    This is intended for stable machine parsing (e.g., container lost markers).
    """
    rec = {"ts_utc": utc_now_iso(), "event": event}
    if fields:
        rec.update(fields)
    line = json.dumps(rec, sort_keys=True, ensure_ascii=False)
    try:
        log_fp.write(line + "\n")
        log_fp.flush()
    except Exception:
        pass


def log_human(log_fp: TextIO, message: str, *, prefix: str = "") -> None:
    """Write a human-readable timestamped line to the run log."""
    try:
        log_fp.write(format_ts_line(prefix, message))
        log_fp.flush()
    except Exception:
        pass


def safe_flush() -> None:
    """Best-effort flush of stdout/stderr (useful before process termination)."""
    for st in (getattr(sys, "stdout", None), getattr(sys, "stderr", None)):
        try:
            if st is not None:
                st.flush()
        except Exception:
            pass


def monotonic_ms() -> int:
    return int(time.monotonic() * 1000)
