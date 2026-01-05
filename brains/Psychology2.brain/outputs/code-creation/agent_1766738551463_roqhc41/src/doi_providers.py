from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
import json, time, random
import urllib.request, urllib.error

DEFAULT_TIMEOUT_S = 12
UA = "cosmo-doi-pipeline/0.1 (+https://example.invalid; mailto:devnull@example.invalid)"

@dataclass
class ProviderError(Exception):
    provider: str
    category: str
    message: str
    status: Optional[int] = None
    retriable: bool = False
    details: Optional[Dict[str, Any]] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "category": self.category,
            "message": self.message,
            "status": self.status,
            "retriable": self.retriable,
            "details": self.details or {},
        }

def _sleep_backoff(attempt: int, retry_after: Optional[float] = None) -> None:
    if retry_after is not None and retry_after > 0:
        time.sleep(min(60.0, retry_after))
        return
    base = min(8.0, 0.6 * (2 ** max(0, attempt - 1)))
    time.sleep(base + random.uniform(0.0, 0.25))

def _parse_retry_after(hdr: Optional[str]) -> Optional[float]:
    if not hdr:
        return None
    try:
        return float(hdr.strip())
    except Exception:
        return None

class BaseProvider:
    name: str = "base"
    base_url: str = ""
    headers: Dict[str, str] = {"User-Agent": UA, "Accept": "application/json"}

    def __init__(self, timeout_s: float = DEFAULT_TIMEOUT_S, max_attempts: int = 4):
        self.timeout_s = float(timeout_s)
        self.max_attempts = int(max_attempts)

    def _get_json(self, url: str) -> Dict[str, Any]:
        last_err: Optional[ProviderError] = None
        for attempt in range(1, self.max_attempts + 1):
            req = urllib.request.Request(url, headers=dict(self.headers), method="GET")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                    status = getattr(resp, "status", None) or 200
                    raw = resp.read()
                    try:
                        return json.loads(raw.decode("utf-8"))
                    except Exception as e:
                        raise ProviderError(self.name, "parse_error", f"Invalid JSON: {e}", status=status, retriable=False)
            except urllib.error.HTTPError as e:
                status = int(getattr(e, "code", 0) or 0)
                retry_after = _parse_retry_after(e.headers.get("Retry-After") if hasattr(e, "headers") else None)
                if status == 404:
                    raise ProviderError(self.name, "not_found", "DOI not found", status=status, retriable=False)
                if status in (400, 422):
                    raise ProviderError(self.name, "bad_request", "Bad request for DOI", status=status, retriable=False)
                if status == 429:
                    last_err = ProviderError(self.name, "rate_limited", "Rate limited", status=status, retriable=True)
                    _sleep_backoff(attempt, retry_after)
                    continue
                if 500 <= status < 600:
                    last_err = ProviderError(self.name, "upstream_error", f"Upstream HTTP {status}", status=status, retriable=True)
                    _sleep_backoff(attempt, retry_after)
                    continue
                raise ProviderError(self.name, "http_error", f"HTTP {status}", status=status, retriable=False)
            except urllib.error.URLError as e:
                last_err = ProviderError(self.name, "network_error", f"Network error: {e}", status=None, retriable=True)
                _sleep_backoff(attempt, None)
                continue
            except TimeoutError as e:
                last_err = ProviderError(self.name, "timeout", f"Timeout: {e}", status=None, retriable=True)
                _sleep_backoff(attempt, None)
                continue
        assert last_err is not None
        raise last_err

    def resolve(self, doi: str) -> Dict[str, Any]:
        raise NotImplementedError

def _first_str(x: Any) -> Optional[str]:
    if x is None:
        return None
    if isinstance(x, str):
        return x.strip() or None
    if isinstance(x, list) and x:
        for v in x:
            if isinstance(v, str) and v.strip():
                return v.strip()
    return None

def _authors_from_crossref(msg: Dict[str, Any]) -> list:
    out = []
    for a in msg.get("author") or []:
        if not isinstance(a, dict):
            continue
        name = " ".join([p for p in [a.get("given"), a.get("family")] if isinstance(p, str) and p.strip()]).strip()
        if name:
            out.append(name)
    return out

def _authors_from_datacite(attrs: Dict[str, Any]) -> list:
    out = []
    for c in attrs.get("creators") or []:
        if not isinstance(c, dict):
            continue
        nm = c.get("name") or c.get("nameType")
        if isinstance(nm, str) and nm.strip():
            out.append(nm.strip())
    return out
class CrossrefProvider(BaseProvider):
    name = "crossref"
    base_url = "https://api.crossref.org/works/"

    def resolve(self, doi: str) -> Dict[str, Any]:
        url = self.base_url + urllib.parse.quote(doi, safe="")
        data = self._get_json(url)
        msg = data.get("message") if isinstance(data, dict) else None
        if not isinstance(msg, dict):
            raise ProviderError(self.name, "parse_error", "Missing Crossref message", retriable=False)
        return {
            "provider": self.name,
            "raw": data,
            "doi": (msg.get("DOI") or doi),
            "title": _first_str(msg.get("title")),
            "publisher": msg.get("publisher") if isinstance(msg.get("publisher"), str) else None,
            "published": (msg.get("created") or msg.get("issued") or {}),
            "type": msg.get("type") if isinstance(msg.get("type"), str) else None,
            "url": msg.get("URL") if isinstance(msg.get("URL"), str) else None,
            "authors": _authors_from_crossref(msg),
            "source": "crossref",
        }

class DataCiteProvider(BaseProvider):
    name = "datacite"
    base_url = "https://api.datacite.org/dois/"

    def resolve(self, doi: str) -> Dict[str, Any]:
        url = self.base_url + urllib.parse.quote(doi, safe="")
        data = self._get_json(url)
        d = data.get("data") if isinstance(data, dict) else None
        attrs = d.get("attributes") if isinstance(d, dict) else None
        if not isinstance(attrs, dict):
            raise ProviderError(self.name, "parse_error", "Missing DataCite attributes", retriable=False)
        return {
            "provider": self.name,
            "raw": data,
            "doi": (attrs.get("doi") or doi),
            "title": _first_str(attrs.get("titles")),
            "publisher": attrs.get("publisher") if isinstance(attrs.get("publisher"), str) else None,
            "published": {"published": attrs.get("published") or attrs.get("publicationYear")},
            "type": attrs.get("types") or {},
            "url": attrs.get("url") if isinstance(attrs.get("url"), str) else None,
            "authors": _authors_from_datacite(attrs),
            "source": "datacite",
        }

def get_default_providers(timeout_s: float = DEFAULT_TIMEOUT_S) -> Tuple[BaseProvider, ...]:
    return (CrossrefProvider(timeout_s=timeout_s), DataCiteProvider(timeout_s=timeout_s))
