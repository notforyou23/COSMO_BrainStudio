from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class ParsingMethod(str, Enum):
    CROSSREF_API = "crossref_api"
    DATACITE_API = "datacite_api"
    LANDING_HTML = "landing_html"
    LANDING_META_TAGS = "landing_meta_tags"
    OTHER = "other"


class FailureReasonCode(str, Enum):
    NONE = "none"
    DOI_INVALID = "doi_invalid"
    DOI_NOT_FOUND = "doi_not_found"
    RESOLUTION_FAILED = "resolution_failed"
    REDIRECT_LOOP = "redirect_loop"
    TIMEOUT = "timeout"
    DNS_ERROR = "dns_error"
    CONNECTION_ERROR = "connection_error"
    TLS_ERROR = "tls_error"
    HTTP_ERROR = "http_error"
    PAYWALL = "paywall"
    ROBOTS_BLOCKED = "robots_blocked"
    RATE_LIMITED = "rate_limited"
    METADATA_NOT_FOUND = "metadata_not_found"
    METADATA_PARSE_FAILED = "metadata_parse_failed"
    LANDING_PARSE_FAILED = "landing_parse_failed"
    UPSTREAM_API_ERROR = "upstream_api_error"
    UNKNOWN = "unknown"


def classify_http_failure(status_code: Optional[int], final_url: Optional[str] = None, body_text: str = "") -> FailureReasonCode:
    if status_code is None:
        return FailureReasonCode.HTTP_ERROR
    if status_code == 404:
        return FailureReasonCode.DOI_NOT_FOUND
    if status_code in (401, 402, 403):
        return FailureReasonCode.PAYWALL
    if status_code == 429:
        return FailureReasonCode.RATE_LIMITED
    if status_code in (451,):
        return FailureReasonCode.ROBOTS_BLOCKED
    t = (body_text or "").lower()
    if status_code == 403 and any(k in t for k in ("robot", "captcha", "forbidden", "access denied")):
        return FailureReasonCode.ROBOTS_BLOCKED
    if status_code in (301, 302, 303, 307, 308) and final_url:
        return FailureReasonCode.RESOLUTION_FAILED
    if 500 <= status_code <= 599:
        return FailureReasonCode.UPSTREAM_API_ERROR
    return FailureReasonCode.HTTP_ERROR


def classify_exception(exc: BaseException) -> FailureReasonCode:
    name = exc.__class__.__name__.lower()
    msg = str(exc).lower()
    if "timeout" in name or "timed out" in msg:
        return FailureReasonCode.TIMEOUT
    if "ssl" in name or "tls" in name or "certificate" in msg:
        return FailureReasonCode.TLS_ERROR
    if "dns" in name or "gaierror" in name or "name or service not known" in msg:
        return FailureReasonCode.DNS_ERROR
    if "connection" in name or "connection" in msg or "reset" in msg:
        return FailureReasonCode.CONNECTION_ERROR
    return FailureReasonCode.UNKNOWN


def normalize_landing_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    u = url.strip()
    if not u:
        return None
    return u


@dataclass(frozen=True)
class Provenance:
    landing_url: Optional[str] = None
    accessed_at: str = ""
    parsing_method: Optional[str] = None
    failure_reason_code: str = FailureReasonCode.NONE.value
    failure_detail: Optional[str] = None

    @staticmethod
    def success(landing_url: Optional[str], parsing_method: ParsingMethod | str, accessed_at: Optional[str] = None) -> "Provenance":
        pm = parsing_method.value if isinstance(parsing_method, ParsingMethod) else str(parsing_method)
        return Provenance(
            landing_url=normalize_landing_url(landing_url),
            accessed_at=accessed_at or utc_now_iso(),
            parsing_method=pm,
            failure_reason_code=FailureReasonCode.NONE.value,
            failure_detail=None,
        )

    @staticmethod
    def failure(
        code: FailureReasonCode | str,
        landing_url: Optional[str] = None,
        parsing_method: ParsingMethod | str | None = None,
        failure_detail: Optional[str] = None,
        accessed_at: Optional[str] = None,
    ) -> "Provenance":
        c = code.value if isinstance(code, FailureReasonCode) else str(code)
        pm = None if parsing_method is None else (parsing_method.value if isinstance(parsing_method, ParsingMethod) else str(parsing_method))
        return Provenance(
            landing_url=normalize_landing_url(landing_url),
            accessed_at=accessed_at or utc_now_iso(),
            parsing_method=pm,
            failure_reason_code=c,
            failure_detail=failure_detail,
        )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if not d.get("accessed_at"):
            d["accessed_at"] = utc_now_iso()
        return d
