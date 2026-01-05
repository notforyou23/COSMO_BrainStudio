from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional
from datetime import datetime, timezone
import json


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class FailureCode(str, Enum):
    NONE = "none"
    INVALID_DOI = "invalid_doi"
    HTTP_ERROR = "http_error"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    NOT_FOUND = "not_found"
    PARSE_ERROR = "parse_error"
    NO_OPEN_ACCESS = "no_open_access"
    SOURCE_ERROR = "source_error"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"


@dataclass
class LicenseInfo:
    license: Optional[str] = None
    license_url: Optional[str] = None
    is_oa: Optional[bool] = None
    is_pd: Optional[bool] = None
    oa_status: Optional[str] = None
    evidence: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> "LicenseInfo":
        if not d:
            return LicenseInfo()
        return LicenseInfo(
            license=d.get("license"),
            license_url=d.get("license_url"),
            is_oa=d.get("is_oa"),
            is_pd=d.get("is_pd"),
            oa_status=d.get("oa_status"),
            evidence=d.get("evidence"),
        )


@dataclass
class RetrievalAttempt:
    ts: str = field(default_factory=utc_now_iso)
    doi: str = ""
    doi_normalized: Optional[str] = None
    source: str = ""
    url: Optional[str] = None
    ok: bool = False
    status_code: Optional[int] = None
    failure_code: FailureCode = FailureCode.UNKNOWN
    failure_reason: Optional[str] = None
    elapsed_ms: Optional[int] = None
    content_type: Optional[str] = None
    final_url: Optional[str] = None
    license: LicenseInfo = field(default_factory=LicenseInfo)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["failure_code"] = self.failure_code.value if isinstance(self.failure_code, FailureCode) else str(self.failure_code)
        d["license"] = self.license.to_dict() if self.license else {}
        return {k: v for k, v in d.items() if v not in (None, {}, [])}

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "RetrievalAttempt":
        return RetrievalAttempt(
            ts=d.get("ts") or utc_now_iso(),
            doi=d.get("doi", ""),
            doi_normalized=d.get("doi_normalized"),
            source=d.get("source", ""),
            url=d.get("url"),
            ok=bool(d.get("ok", False)),
            status_code=d.get("status_code"),
            failure_code=FailureCode(d.get("failure_code", FailureCode.UNKNOWN.value)),
            failure_reason=d.get("failure_reason"),
            elapsed_ms=d.get("elapsed_ms"),
            content_type=d.get("content_type"),
            final_url=d.get("final_url"),
            license=LicenseInfo.from_dict(d.get("license")),
            extra=d.get("extra") or {},
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)


@dataclass
class RetrievalSummary:
    doi: str
    doi_normalized: Optional[str] = None
    best_url: Optional[str] = None
    best_source: Optional[str] = None
    ok: bool = False
    failure_code: FailureCode = FailureCode.UNKNOWN
    failure_reason: Optional[str] = None
    license: LicenseInfo = field(default_factory=LicenseInfo)
    attempts: List[RetrievalAttempt] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["failure_code"] = self.failure_code.value if isinstance(self.failure_code, FailureCode) else str(self.failure_code)
        d["license"] = self.license.to_dict() if self.license else {}
        d["attempts"] = [a.to_dict() for a in self.attempts]
        return {k: v for k, v in d.items() if v not in (None, {}, [])}


def flatten_attempt_for_csv(a: RetrievalAttempt) -> Dict[str, Any]:
    d = a.to_dict()
    lic = d.pop("license", {}) or {}
    for k, v in lic.items():
        d[f"license_{k}"] = v
    extra = d.pop("extra", {}) or {}
    for k, v in extra.items():
        d[f"extra_{k}"] = v
    return d


def infer_summary_from_attempts(doi: str, doi_normalized: Optional[str], attempts: Iterable[RetrievalAttempt]) -> RetrievalSummary:
    attempts_l = list(attempts)
    ok_attempts = [a for a in attempts_l if a.ok and (a.url or a.final_url)]
    best = ok_attempts[0] if ok_attempts else (attempts_l[0] if attempts_l else None)
    if best and best.ok:
        return RetrievalSummary(
            doi=doi,
            doi_normalized=doi_normalized,
            best_url=best.final_url or best.url,
            best_source=best.source,
            ok=True,
            failure_code=FailureCode.NONE,
            license=best.license or LicenseInfo(),
            attempts=attempts_l,
        )
    fc = best.failure_code if best else FailureCode.UNKNOWN
    fr = best.failure_reason if best else "no_attempts"
    return RetrievalSummary(
        doi=doi,
        doi_normalized=doi_normalized,
        ok=False,
        failure_code=fc,
        failure_reason=fr,
        attempts=attempts_l,
    )
