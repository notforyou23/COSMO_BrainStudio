"""Shared user-agent and polite request defaults for QA link checking.

This module intentionally has no third-party dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from email.utils import formatdate
from typing import Dict, Optional, Tuple


DEFAULT_UA_PRODUCT = "COSMO-QA-LinkCheck"
DEFAULT_UA_VERSION = "1.0"
DEFAULT_CONTACT = "linkcheck@local"
DEFAULT_ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
DEFAULT_ACCEPT_LANGUAGE = "en-US,en;q=0.8"
DEFAULT_ACCEPT_ENCODING = "identity"
DEFAULT_CACHE_CONTROL = "no-cache"
DEFAULT_PRAGMA = "no-cache"


@dataclass(frozen=True)
class PoliteRequestConfig:
    """Defaults that aim to be polite and predictable during link checking."""

    user_agent: str = f"{DEFAULT_UA_PRODUCT}/{DEFAULT_UA_VERSION} (+{DEFAULT_CONTACT})"
    accept: str = DEFAULT_ACCEPT
    accept_language: str = DEFAULT_ACCEPT_LANGUAGE
    accept_encoding: str = DEFAULT_ACCEPT_ENCODING
    cache_control: str = DEFAULT_CACHE_CONTROL
    pragma: str = DEFAULT_PRAGMA
    max_redirects: int = 10
    timeout_s: float = 15.0
    connect_timeout_s: Optional[float] = None
    read_timeout_s: Optional[float] = None
    retries: int = 1
    backoff_s: float = 0.6
    rate_limit_per_host_rps: float = 1.0
    min_delay_s: float = 0.2


DEFAULTS = PoliteRequestConfig()
def build_user_agent(
    product: str = DEFAULT_UA_PRODUCT,
    version: str = DEFAULT_UA_VERSION,
    contact: str = DEFAULT_CONTACT,
    comment: Optional[str] = None,
) -> str:
    """Return a conservative UA string suitable for automated link checks."""
    base = f"{product}/{version} (+{contact})"
    if comment:
        return f"{base} {comment}"
    return base


def default_headers(
    cfg: PoliteRequestConfig = DEFAULTS,
    extra: Optional[Dict[str, str]] = None,
    include_date: bool = False,
) -> Dict[str, str]:
    """Construct default request headers (no cookies, no compression by default)."""
    headers: Dict[str, str] = {
        "User-Agent": cfg.user_agent,
        "Accept": cfg.accept,
        "Accept-Language": cfg.accept_language,
        "Accept-Encoding": cfg.accept_encoding,
        "Cache-Control": cfg.cache_control,
        "Pragma": cfg.pragma,
        "Connection": "close",
    }
    if include_date:
        headers["Date"] = formatdate(usegmt=True)
    if extra:
        for k, v in extra.items():
            if v is None:
                continue
            headers[str(k)] = str(v)
    return headers


def timeout_tuple(cfg: PoliteRequestConfig = DEFAULTS) -> Tuple[float, float]:
    """Return (connect_timeout, read_timeout) for HTTP clients that accept tuples."""
    ct = cfg.connect_timeout_s if cfg.connect_timeout_s is not None else float(cfg.timeout_s)
    rt = cfg.read_timeout_s if cfg.read_timeout_s is not None else float(cfg.timeout_s)
    return float(ct), float(rt)
