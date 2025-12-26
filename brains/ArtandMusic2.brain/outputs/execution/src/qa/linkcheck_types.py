from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence
JsonDict = Dict[str, Any]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
@dataclass(frozen=True)
class LinkSource:
    case_study_path: str
    locator: str = ""  # e.g. JSON pointer /exemplar_urls/0
    note: str = ""

    def to_dict(self) -> JsonDict:
        return {"case_study_path": self.case_study_path, "locator": self.locator, "note": self.note}

    @staticmethod
    def from_dict(d: JsonDict) -> "LinkSource":
        return LinkSource(
            case_study_path=str(d.get("case_study_path", "")),
            locator=str(d.get("locator", "")),
            note=str(d.get("note", "")),
        )
@dataclass(frozen=True)
class RedirectHop:
    url: str
    status_code: int

    def to_dict(self) -> JsonDict:
        return {"url": self.url, "status_code": int(self.status_code)}

    @staticmethod
    def from_dict(d: JsonDict) -> "RedirectHop":
        return RedirectHop(url=str(d.get("url", "")), status_code=int(d.get("status_code", 0)))
@dataclass
class LinkCheckResult:
    url: str
    ok: bool
    status_code: Optional[int] = None
    final_url: Optional[str] = None
    redirects: List[RedirectHop] = field(default_factory=list)
    error: Optional[str] = None
    checked_at: str = field(default_factory=utc_now_iso)
    sources: List[LinkSource] = field(default_factory=list)

    def to_dict(self) -> JsonDict:
        return {
            "url": self.url,
            "ok": bool(self.ok),
            "status_code": self.status_code,
            "final_url": self.final_url,
            "redirects": [h.to_dict() for h in self.redirects],
            "error": self.error,
            "checked_at": self.checked_at,
            "sources": [s.to_dict() for s in self.sources],
        }

    @staticmethod
    def from_dict(d: JsonDict) -> "LinkCheckResult":
        redirects = [RedirectHop.from_dict(x) for x in (d.get("redirects") or []) if isinstance(x, dict)]
        sources = [LinkSource.from_dict(x) for x in (d.get("sources") or []) if isinstance(x, dict)]
        return LinkCheckResult(
            url=str(d.get("url", "")),
            ok=bool(d.get("ok", False)),
            status_code=d.get("status_code", None),
            final_url=d.get("final_url", None),
            redirects=redirects,
            error=d.get("error", None),
            checked_at=str(d.get("checked_at", utc_now_iso())),
            sources=sources,
        )
@dataclass
class LinkCheckStats:
    total: int = 0
    ok: int = 0
    failed: int = 0
    redirected: int = 0

    def to_dict(self) -> JsonDict:
        return {
            "total": int(self.total),
            "ok": int(self.ok),
            "failed": int(self.failed),
            "redirected": int(self.redirected),
        }

    @staticmethod
    def from_results(results: Sequence[LinkCheckResult]) -> "LinkCheckStats":
        total = len(results)
        ok = sum(1 for r in results if r.ok)
        failed = total - ok
        redirected = sum(1 for r in results if r.redirects)
        return LinkCheckStats(total=total, ok=ok, failed=failed, redirected=redirected)

    @staticmethod
    def from_dict(d: JsonDict) -> "LinkCheckStats":
        return LinkCheckStats(
            total=int(d.get("total", 0)),
            ok=int(d.get("ok", 0)),
            failed=int(d.get("failed", 0)),
            redirected=int(d.get("redirected", 0)),
        )
@dataclass
class LinkCheckReport:
    generated_at: str = field(default_factory=utc_now_iso)
    results: List[LinkCheckResult] = field(default_factory=list)
    stats: LinkCheckStats = field(default_factory=LinkCheckStats)
    schema_version: str = "1"

    def recompute_stats(self) -> None:
        self.stats = LinkCheckStats.from_results(self.results)

    def to_dict(self) -> JsonDict:
        if self.stats.total == 0 and self.results:
            self.recompute_stats()
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "stats": self.stats.to_dict(),
            "results": [r.to_dict() for r in self.results],
        }

    @staticmethod
    def from_dict(d: JsonDict) -> "LinkCheckReport":
        results = [LinkCheckResult.from_dict(x) for x in (d.get("results") or []) if isinstance(x, dict)]
        stats_d = d.get("stats") or {}
        rep = LinkCheckReport(
            schema_version=str(d.get("schema_version", "1")),
            generated_at=str(d.get("generated_at", utc_now_iso())),
            results=results,
            stats=LinkCheckStats.from_dict(stats_d) if isinstance(stats_d, dict) else LinkCheckStats(),
        )
        if rep.stats.total == 0 and rep.results:
            rep.recompute_stats()
        return rep
