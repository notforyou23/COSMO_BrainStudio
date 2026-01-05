from __future__ import annotations

import contextvars
import json
import logging
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional


correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="")
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


def _utc_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def ensure_correlation_id(value: Optional[str] = None) -> str:
    cid = value or correlation_id_var.get() or uuid.uuid4().hex
    correlation_id_var.set(cid)
    return cid


def ensure_request_id(value: Optional[str] = None) -> str:
    rid = value or request_id_var.get() or uuid.uuid4().hex
    request_id_var.set(rid)
    return rid


def set_ids(*, correlation_id: Optional[str] = None, request_id: Optional[str] = None) -> Dict[str, str]:
    return {
        "correlation_id": ensure_correlation_id(correlation_id),
        "request_id": ensure_request_id(request_id),
    }


class JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base: Dict[str, Any] = {
            "ts": _utc_ts(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id_var.get() or None,
            "request_id": request_id_var.get() or None,
        }
        extra = getattr(record, "extra", None)
        if isinstance(extra, dict):
            for k, v in extra.items():
                if k not in base:
                    base[k] = v
        if record.exc_info:
            base["exc_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
            base["exc"] = self.formatException(record.exc_info)
        return json.dumps(base, ensure_ascii=False, separators=(",", ":"))


def setup_json_logging(
    name: str = "citation_mvp",
    *,
    level: int = logging.INFO,
    stream=None,
    clear_handlers: bool = True,
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False
    if clear_handlers:
        logger.handlers.clear()
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(JsonLineFormatter())
    logger.addHandler(handler)
    return logger


def log_event(logger: logging.Logger, event: str, *, level: int = logging.INFO, **fields: Any) -> None:
    payload = {"event": event, **fields}
    logger.log(level, event, extra={"extra": payload})


def _safe_reason(reason: Any, max_len: int = 500) -> Any:
    if reason is None:
        return None
    if isinstance(reason, (int, float, bool, dict, list)):
        return reason
    s = str(reason)
    return s if len(s) <= max_len else s[: max_len - 3] + "..."


@dataclass
class AttemptResult:
    provider: str
    doi: Optional[str] = None
    ok: bool = False
    duration_ms: int = 0
    status_code: Optional[int] = None
    reason: Optional[Any] = None
    url: Optional[str] = None
    content_type: Optional[str] = None
    bytes: Optional[int] = None


@contextmanager
def provider_attempt(
    logger: logging.Logger,
    *,
    provider: str,
    doi: Optional[str] = None,
    correlation_id: Optional[str] = None,
    request_id: Optional[str] = None,
    **start_fields: Any,
):
    ids = set_ids(correlation_id=correlation_id, request_id=request_id)
    start = time.perf_counter()
    log_event(logger, "provider_attempt_start", provider=provider, doi=doi, **ids, **start_fields)
    result = AttemptResult(provider=provider, doi=doi, ok=False)
    try:
        yield result
        result.ok = bool(result.ok)
    except Exception as e:
        result.ok = False
        result.reason = _safe_reason(e)
        log_event(logger, "provider_attempt_error", level=logging.ERROR, provider=provider, doi=doi, **ids, error=_safe_reason(e))
        raise
    finally:
        result.duration_ms = int((time.perf_counter() - start) * 1000)
        data = asdict(result)
        data["reason"] = _safe_reason(data.get("reason"))
        log_event(logger, "provider_attempt_end", provider=provider, doi=doi, **ids, **data)


def with_ids(fields: Optional[Dict[str, Any]] = None, *, correlation_id: Optional[str] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
    ids = set_ids(correlation_id=correlation_id, request_id=request_id)
    out: Dict[str, Any] = {}
    if fields:
        out.update(fields)
    out.update(ids)
    return out


def summarize_attempts(attempts: Iterable[AttemptResult]) -> Dict[str, Any]:
    a = list(attempts)
    total = len(a)
    ok = sum(1 for x in a if x.ok)
    by_provider: Dict[str, Dict[str, int]] = {}
    for x in a:
        p = x.provider
        d = by_provider.setdefault(p, {"total": 0, "ok": 0})
        d["total"] += 1
        d["ok"] += 1 if x.ok else 0
    return {"total": total, "ok": ok, "by_provider": by_provider}
