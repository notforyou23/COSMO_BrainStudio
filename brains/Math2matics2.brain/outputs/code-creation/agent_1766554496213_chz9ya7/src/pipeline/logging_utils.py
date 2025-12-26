"""Logging utilities for deterministic, run-scoped file logging.

This module configures per-run log files under outputs/logs with stable,
machine-parseable formatting and a consistent set of record fields.
"""

from __future__ import annotations

import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple


_DEFAULT_FMT = (
    "%(asctime)sZ | %(levelname)s | %(name)s | run_id=%(run_id)s | "
    "pid=%(process)d | %(message)s"
)


class _UTCISOFormatter(logging.Formatter):
    """UTC ISO-8601 formatter with millisecond precision and fixed schema."""

    converter = time.gmtime

    def formatTime(self, record, datefmt=None):  # noqa: N802 (logging API)
        t = time.strftime("%Y-%m-%dT%H:%M:%S", self.converter(record.created))
        ms = int(record.msecs)
        return f"{t}.{ms:03d}"


class _RunIdFilter(logging.Filter):
    def __init__(self, run_id: str):
        super().__init__()
        self.run_id = run_id

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "run_id"):
            record.run_id = self.run_id
        return True


def _sanitize_token(token: str) -> str:
    token = (token or "").strip()
    token = re.sub(r"[^A-Za-z0-9_.-]+", "_", token)
    return token or "run"


def _outputs_logs_dir(outputs_dir: Path) -> Path:
    return Path(outputs_dir).joinpath("outputs", "logs")


@dataclass(frozen=True)
class LogConfig:
    run_id: str
    log_path: Path
    logger_name: str
    level: int


def configure_run_file_logger(
    outputs_dir: Path,
    run_id: str,
    logger_name: str = "pipeline",
    level: int = logging.INFO,
    console: bool = False,
) -> Tuple[logging.Logger, LogConfig]:
    """Configure a run-scoped logger writing to outputs/logs.

    Returns (logger, LogConfig). Safe to call multiple times: handlers are reset.
    """
    out_dir = Path(outputs_dir)
    logs_dir = _outputs_logs_dir(out_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)

    safe_run_id = _sanitize_token(run_id)
    safe_name = _sanitize_token(logger_name)
    log_path = logs_dir.joinpath(f"{safe_name}_{safe_run_id}.log")

    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    logger.propagate = False

    for h in list(logger.handlers):
        logger.removeHandler(h)
        try:
            h.close()
        except Exception:
            pass

    filt = _RunIdFilter(safe_run_id)
    formatter = _UTCISOFormatter(_DEFAULT_FMT)

    file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8", delay=False)
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(filt)
    logger.addHandler(file_handler)

    if console:
        stream_handler = logging.StreamHandler(stream=sys.stdout)
        stream_handler.setLevel(level)
        stream_handler.setFormatter(formatter)
        stream_handler.addFilter(filt)
        logger.addHandler(stream_handler)

    logger.debug(
        "logger_configured",
        extra={"run_id": safe_run_id},
    )

    return logger, LogConfig(run_id=safe_run_id, log_path=log_path, logger_name=logger_name, level=level)


def log_reproducibility_context(
    logger: logging.Logger,
    *,
    seed: Optional[int] = None,
    python_hash_seed: Optional[str] = None,
    extra: Optional[dict] = None,
) -> None:
    """Emit a single, stable key-value line describing reproducibility context."""
    payload = {
        "event": "reproducibility_context",
        "seed": seed,
        "python_hash_seed": python_hash_seed if python_hash_seed is not None else os.environ.get("PYTHONHASHSEED"),
    }
    if extra:
        payload.update(extra)
    msg = " | ".join(f"{k}={payload[k]!r}" for k in sorted(payload.keys()))
    logger.info(msg)


def get_run_log_path(outputs_dir: Path, run_id: str, logger_name: str = "pipeline") -> Path:
    """Compute the run log path without configuring logging."""
    logs_dir = _outputs_logs_dir(Path(outputs_dir))
    return logs_dir.joinpath(f"{_sanitize_token(logger_name)}_{_sanitize_token(run_id)}.log")
