from __future__ import annotations

import contextvars
import datetime as _dt
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

_run_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("run_id", default="-")
_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

def set_run_id(run_id: str) -> None:
    _run_id_var.set(run_id or "-")

def get_run_id() -> str:
    return _run_id_var.get()

def set_request_id(request_id: str) -> None:
    _request_id_var.set(request_id or "-")

def get_request_id() -> str:
    return _request_id_var.get()

def utc_now_iso() -> str:
    return _dt.datetime.now(tz=_dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

@dataclass(frozen=True)
class LogPaths:
    artifacts_dir: Path
    log_jsonl: Path
    log_txt: Path

class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "ts": utc_now_iso(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "run_id": getattr(record, "run_id", get_run_id()),
            "request_id": getattr(record, "request_id", get_request_id()),
        }
        for k, v in getattr(record, "__dict__", {}).items():
            if k in ("args", "msg", "exc_info", "exc_text", "stack_info", "lineno", "msecs", "relativeCreated",
                     "thread", "threadName", "processName", "process", "created", "name", "levelname", "levelno",
                     "pathname", "filename", "module", "funcName"):
                continue
            if k in payload:
                continue
            try:
                json.dumps(v)
                payload[k] = v
            except Exception:
                payload[k] = repr(v)
        if record.exc_info:
            payload["exc_type"] = getattr(record.exc_info[0], "__name__", "Exception")
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)

class _ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = get_run_id()
        record.request_id = get_request_id()
        return True

def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def _parse_level(level: str) -> int:
    return getattr(logging, str(level or "INFO").upper(), logging.INFO)

def new_run_id() -> str:
    return uuid.uuid4().hex

def setup_logging(
    artifacts_dir: Path,
    *,
    run_id: Optional[str] = None,
    level: str = "INFO",
    logger_name: str = "doi_api",
) -> Tuple[logging.Logger, LogPaths]:
    _ensure_dir(artifacts_dir)
    run_id_final = (run_id or os.environ.get("RUN_ID") or new_run_id()).strip() or "-"
    set_run_id(run_id_final)

    log_jsonl = artifacts_dir / f"logs_{run_id_final}.jsonl"
    log_txt = artifacts_dir / f"logs_{run_id_final}.log"
    paths = LogPaths(artifacts_dir=artifacts_dir, log_jsonl=log_jsonl, log_txt=log_txt)

    logger = logging.getLogger(logger_name)
    logger.setLevel(_parse_level(level))
    logger.propagate = False

    for h in list(logger.handlers):
        logger.removeHandler(h)

    ctx_filter = _ContextFilter()

    fh_json = logging.FileHandler(log_jsonl, encoding="utf-8")
    fh_json.setLevel(logger.level)
    fh_json.setFormatter(_JsonFormatter())
    fh_json.addFilter(ctx_filter)

    fh_txt = logging.FileHandler(log_txt, encoding="utf-8")
    fh_txt.setLevel(logger.level)
    fh_txt.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s run_id=%(run_id)s request_id=%(request_id)s %(message)s"))
    fh_txt.addFilter(ctx_filter)

    sh = logging.StreamHandler()
    sh.setLevel(logger.level)
    sh.setFormatter(_JsonFormatter())
    sh.addFilter(ctx_filter)

    logger.addHandler(fh_json)
    logger.addHandler(fh_txt)
    logger.addHandler(sh)

    logger.info("logging_initialized", extra={"artifacts_dir": str(artifacts_dir), "log_jsonl": str(log_jsonl), "log_txt": str(log_txt)})
    return logger, paths

class request_timer:
    def __init__(self, logger: logging.Logger, *, event: str = "request_complete", extra: Optional[Dict[str, Any]] = None):
        self.logger = logger
        self.event = event
        self.extra = extra or {}
        self._t0: float = 0.0

    def __enter__(self) -> "request_timer":
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        ms = (time.perf_counter() - self._t0) * 1000.0
        data = dict(self.extra)
        data["duration_ms"] = round(ms, 3)
        if exc_type is None:
            self.logger.info(self.event, extra=data)
            return False
        data["error_type"] = getattr(exc_type, "__name__", "Exception")
        self.logger.error(self.event, extra=data, exc_info=(exc_type, exc, tb))
        return False
