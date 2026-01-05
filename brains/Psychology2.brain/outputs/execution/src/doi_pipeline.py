from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union
import re
import time
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)

FAIL_INVALID = "invalid_doi"
FAIL_NOT_FOUND = "not_found"
FAIL_PROVIDER_ERROR = "provider_error"
FAIL_RATE_LIMITED = "rate_limited"
FAIL_TIMEOUT = "timeout"
FAIL_NETWORK = "network_error"
FAIL_UNEXPECTED = "unexpected"
FAIL_NO_SUCCESS = "no_providers_succeeded"
def normalize_doi(value: str) -> str:
    s = (value or "").strip()
    s = re.sub(r"^doi\s*:\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s, flags=re.IGNORECASE)
    s = s.strip().strip(".")
    return s.lower()

def validate_doi(doi: str) -> Tuple[bool, str]:
    if not doi:
        return False, "empty DOI"
    if any(ch.isspace() for ch in doi):
        return False, "contains whitespace"
    if not DOI_RE.match(doi):
        return False, "does not match DOI pattern"
    return True, 
@dataclass
class ProviderAttempt:
    provider: str
    ok: bool
    category: Optional[str] = None
    reason: Optional[str] = None
    http_status: Optional[int] = None
    elapsed_ms: Optional[int] = None

@dataclass
class DOIResult:
    doi_input: str
    doi: Optional[str]
    ok: bool
    category: Optional[str] = None
    reason: Optional[str] = None
    provider: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    attempts: List[ProviderAttempt] = field(default_factory=list)

def _provider_name(p: Any) -> str:
    return getattr(p, "name", None) or getattr(p, "__name__", None) or p.__class__.__name__

def _as_http_status(x: Any) -> Optional[int]:
    for k in ("status", "status_code", "http_status"):
        v = getattr(x, k, None)
        if isinstance(v, int):
            return v
    if isinstance(x, dict):
        v = x.get("http_status") or x.get("status") or x.get("status_code")
        if isinstance(v, int):
            return v
    return None
def _call_provider(provider: Any, doi: str) -> Any:
    # Provider may be callable or expose resolve().
    if callable(provider) and not hasattr(provider, "resolve"):
        return provider(doi)
    return provider.resolve(doi)

def _parse_provider_response(resp: Any) -> Tuple[bool, Dict[str, Any], Optional[str], Optional[str], Optional[int]]:
    # Supports: dict with {ok, metadata, category, reason, http_status} or (ok, metadata, category, reason, http_status)
    if isinstance(resp, tuple) and len(resp) >= 2:
        ok = bool(resp[0])
        md = resp[1] or {}
        cat = resp[2] if len(resp) > 2 else None
        rea = resp[3] if len(resp) > 3 else None
        hs = resp[4] if len(resp) > 4 else None
        return ok, dict(md), cat, rea, hs if isinstance(hs, int) else None
    if isinstance(resp, dict):
        ok = bool(resp.get("ok", resp.get("success", False)))
        md = resp.get("metadata") or resp.get("data") or {}
        cat = resp.get("category")
        rea = resp.get("reason") or resp.get("error")
        hs = resp.get("http_status") or resp.get("status_code") or resp.get("status")
        return ok, dict(md or {}), cat, rea, hs if isinstance(hs, int) else None
    # Unknown object with attributes
    ok = bool(getattr(resp, "ok", getattr(resp, "success", False)))
    md = getattr(resp, "metadata", getattr(resp, "data", {})) or {}
    cat = getattr(resp, "category", None)
    rea = getattr(resp, "reason", getattr(resp, "error", None))
    hs = _as_http_status(resp)
    return ok, dict(md), cat, rea, hs
def resolve_doi(
    doi_input: str,
    providers: Sequence[Any],
) -> DOIResult:
    doi = normalize_doi(doi_input)
    valid, v_reason = validate_doi(doi)
    if not valid:
        return DOIResult(doi_input=doi_input, doi=doi or None, ok=False, category=FAIL_INVALID, reason=v_reason)

    attempts: List[ProviderAttempt] = []
    best_fail: Optional[ProviderAttempt] = None

    for p in providers:
        name = _provider_name(p)
        t0 = time.time()
        try:
            resp = _call_provider(p, doi)
            ok, md, cat, rea, hs = _parse_provider_response(resp)
            elapsed = int((time.time() - t0) * 1000)
            if ok:
                attempts.append(ProviderAttempt(provider=name, ok=True, elapsed_ms=elapsed, http_status=hs))
                return DOIResult(
                    doi_input=doi_input,
                    doi=doi,
                    ok=True,
                    provider=name,
                    metadata=md or {},
                    attempts=attempts,
                )
            cat = cat or (FAIL_NOT_FOUND if hs == 404 else FAIL_PROVIDER_ERROR)
            rea = rea or ("not found" if cat == FAIL_NOT_FOUND else "provider returned unsuccessful response")
            a = ProviderAttempt(provider=name, ok=False, category=cat, reason=rea, http_status=hs, elapsed_ms=elapsed)
            attempts.append(a)
        except TimeoutError as e:
            elapsed = int((time.time() - t0) * 1000)
            a = ProviderAttempt(provider=name, ok=False, category=FAIL_TIMEOUT, reason=str(e) or "timeout", elapsed_ms=elapsed)
            attempts.append(a)
        except Exception as e:
            elapsed = int((time.time() - t0) * 1000)
            msg = str(e) or e.__class__.__name__
            cat = FAIL_UNEXPECTED
            if any(k in msg.lower() for k in ("429", "rate limit", "too many requests")):
                cat = FAIL_RATE_LIMITED
            elif any(k in msg.lower() for k in ("timeout", "timed out")):
                cat = FAIL_TIMEOUT
            elif any(k in msg.lower() for k in ("connection", "dns", "network", "ssl", "http")):
                cat = FAIL_NETWORK
            a = ProviderAttempt(provider=name, ok=False, category=cat, reason=msg, elapsed_ms=elapsed)
            attempts.append(a)

        if best_fail is None:
            best_fail = attempts[-1]
        else:
            prio = {FAIL_RATE_LIMITED: 1, FAIL_TIMEOUT: 2, FAIL_NETWORK: 3, FAIL_PROVIDER_ERROR: 4, FAIL_NOT_FOUND: 5, FAIL_UNEXPECTED: 6}
            if prio.get(attempts[-1].category or "", 9) < prio.get(best_fail.category or "", 9):
                best_fail = attempts[-1]

    reason = (best_fail.reason if best_fail else "no providers configured") or "no providers succeeded"
    category = (best_fail.category if best_fail else FAIL_NO_SUCCESS) or FAIL_NO_SUCCESS
    return DOIResult(doi_input=doi_input, doi=doi, ok=False, category=category, reason=reason, attempts=attempts)
def resolve_many(
    dois: Iterable[str],
    providers: Sequence[Any],
) -> Dict[str, Any]:
    results: List[DOIResult] = []
    for d in dois:
        results.append(resolve_doi(d, providers))

    summary = {
        "total": len(results),
        "ok": sum(1 for r in results if r.ok),
        "failed": sum(1 for r in results if not r.ok),
        "by_category": {},
    }
    by_cat: Dict[str, int] = {}
    for r in results:
        if not r.ok:
            by_cat[r.category or FAIL_NO_SUCCESS] = by_cat.get(r.category or FAIL_NO_SUCCESS, 0) + 1
    summary["by_category"] = dict(sorted(by_cat.items(), key=lambda kv: (-kv[1], kv[0])))

    return {
        "results": [asdict(r) for r in results],
        "summary": summary,
    }
