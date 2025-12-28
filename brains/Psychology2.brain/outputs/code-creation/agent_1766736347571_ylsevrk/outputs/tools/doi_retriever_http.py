from __future__ import annotations
import json as _json
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import requests
from requests import Response
@dataclass
class HttpErrorNormalized(Exception):
    kind: str
    message: str
    url: Optional[str] = None
    source: Optional[str] = None
    status_code: Optional[int] = None
    retryable: bool = False
    detail: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "message": self.message,
            "url": self.url,
            "source": self.source,
            "status_code": self.status_code,
            "retryable": self.retryable,
            "detail": self.detail or {},
        }
def _host(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").lower()
    except Exception:
        return ""

class RateLimiter:
    def __init__(self, min_interval_s: float = 0.2):
        self.min_interval_s = float(min_interval_s)
        self._last: Dict[str, float] = {}

    def wait(self, url: str) -> None:
        h = _host(url) or "_"
        now = time.time()
        last = self._last.get(h, 0.0)
        dt = now - last
        if dt < self.min_interval_s:
            time.sleep(self.min_interval_s - dt)
        self._last[h] = time.time()
def build_headers(email: Optional[str] = None, user_agent: Optional[str] = None, accept: Optional[str] = None) -> Dict[str, str]:
    ua = user_agent or "doi-retriever/0.1"
    if email and "mailto:" not in ua:
        ua = f"{ua} (mailto:{email})"
    h = {"User-Agent": ua}
    if accept:
        h["Accept"] = accept
    return h

def build_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"Accept-Encoding": "gzip, deflate"})
    return s
def normalize_error(exc: Exception, url: Optional[str] = None, source: Optional[str] = None) -> HttpErrorNormalized:
    if isinstance(exc, HttpErrorNormalized):
        return exc
    if isinstance(exc, requests.Timeout):
        return HttpErrorNormalized("timeout", str(exc) or "Request timed out", url=url, source=source, retryable=True)
    if isinstance(exc, requests.ConnectionError):
        return HttpErrorNormalized("connection_error", str(exc) or "Connection error", url=url, source=source, retryable=True)
    if isinstance(exc, requests.RequestException):
        return HttpErrorNormalized("request_error", str(exc) or "Request error", url=url, source=source, retryable=True)
    return HttpErrorNormalized("unknown_error", str(exc) or "Unknown error", url=url, source=source, retryable=False)

def _response_error(resp: Response, url: str, source: Optional[str]) -> HttpErrorNormalized:
    retryable = resp.status_code in (408, 425, 429, 500, 502, 503, 504)
    detail: Dict[str, Any] = {"headers": dict(resp.headers)}
    try:
        ct = (resp.headers.get("Content-Type") or "").lower()
        if "json" in ct:
            detail["body_json"] = resp.json()
        else:
            detail["body_text"] = (resp.text or "")[:2000]
    except Exception:
        pass
    return HttpErrorNormalized(
        kind="http_error",
        message=f"HTTP {resp.status_code}",
        url=url,
        source=source,
        status_code=resp.status_code,
        retryable=retryable,
        detail=detail,
    )
def request(
    method: str,
    url: str,
    *,
    source: Optional[str] = None,
    session: Optional[requests.Session] = None,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    data: Any = None,
    json_data: Any = None,
    timeout_s: float = 20.0,
    max_retries: int = 3,
    backoff_s: float = 0.8,
    rate_limiter: Optional[RateLimiter] = None,
    allow_redirects: bool = True,
) -> Response:
    sess = session or build_session()
    h = dict(sess.headers)
    if headers:
        h.update(headers)
    last_exc: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        if rate_limiter:
            rate_limiter.wait(url)
        try:
            resp = sess.request(
                method.upper(),
                url,
                params=params,
                headers=h,
                data=data,
                json=json_data,
                timeout=timeout_s,
                allow_redirects=allow_redirects,
            )
            if resp.status_code >= 400:
                err = _response_error(resp, url, source)
                if err.retryable and attempt < max_retries:
                    time.sleep(backoff_s * (2 ** attempt))
                    continue
                raise err
            return resp
        except Exception as e:
            ne = normalize_error(e, url=url, source=source)
            last_exc = ne
            if ne.retryable and attempt < max_retries:
                time.sleep(backoff_s * (2 ** attempt))
                continue
            raise ne
    raise normalize_error(last_exc or Exception("unreachable"), url=url, source=source)
def get_json(
    url: str,
    *,
    source: Optional[str] = None,
    session: Optional[requests.Session] = None,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout_s: float = 20.0,
    max_retries: int = 3,
    backoff_s: float = 0.8,
    rate_limiter: Optional[RateLimiter] = None,
) -> Tuple[Any, Dict[str, Any]]:
    resp = request(
        "GET",
        url,
        source=source,
        session=session,
        params=params,
        headers=headers,
        timeout_s=timeout_s,
        max_retries=max_retries,
        backoff_s=backoff_s,
        rate_limiter=rate_limiter,
    )
    try:
        data = resp.json()
    except Exception as e:
        raise HttpErrorNormalized(
            kind="parse_error",
            message=f"Failed to parse JSON: {e}",
            url=url,
            source=source,
            status_code=resp.status_code,
            retryable=False,
            detail={"content_type": resp.headers.get("Content-Type"), "body_prefix": (resp.text or "")[:2000]},
        )
    meta = {"final_url": str(resp.url), "status_code": resp.status_code, "headers": dict(resp.headers)}
    return data, meta

def get_text(
    url: str,
    *,
    source: Optional[str] = None,
    session: Optional[requests.Session] = None,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout_s: float = 20.0,
    max_retries: int = 3,
    backoff_s: float = 0.8,
    rate_limiter: Optional[RateLimiter] = None,
) -> Tuple[str, Dict[str, Any]]:
    resp = request(
        "GET",
        url,
        source=source,
        session=session,
        params=params,
        headers=headers,
        timeout_s=timeout_s,
        max_retries=max_retries,
        backoff_s=backoff_s,
        rate_limiter=rate_limiter,
    )
    meta = {"final_url": str(resp.url), "status_code": resp.status_code, "headers": dict(resp.headers)}
    return resp.text or "", meta
