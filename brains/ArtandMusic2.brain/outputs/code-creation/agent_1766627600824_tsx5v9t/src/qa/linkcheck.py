from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
import re
import time
import urllib.parse
import urllib.request
import urllib.error


_URL_RE = re.compile(r"https?://[^\s\]\)\}\>\"\']+", re.IGNORECASE)

_DEFAULT_HEADERS = {
    "User-Agent": "cosmo-linkcheck/1.0 (+https://example.invalid)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _normalize_url(u: str) -> str:
    u = u.strip()
    if not u:
        return u
    try:
        p = urllib.parse.urlsplit(u)
    except Exception:
        return u
    if p.scheme not in ("http", "https"):
        return u
    if not p.netloc:
        return u
    path = p.path or "/"
    return urllib.parse.urlunsplit((p.scheme, p.netloc, path, p.query, p.fragment))


def extract_urls_from_case_study_json(obj: Any) -> List[str]:
    urls: List[str] = []

    def add(u: str) -> None:
        u2 = _normalize_url(u)
        if u2 and u2 not in seen:
            seen.add(u2)
            urls.append(u2)

    def walk(x: Any) -> None:
        if x is None:
            return
        if isinstance(x, str):
            for m in _URL_RE.finditer(x):
                add(m.group(0))
            return
        if isinstance(x, (int, float, bool)):
            return
        if isinstance(x, list):
            for it in x:
                walk(it)
            return
        if isinstance(x, dict):
            for k, v in x.items():
                if isinstance(v, str) and isinstance(k, str) and k.lower() in {
                    "url", "href", "link", "source_url", "canonical_url", "homepage",
                    "repository", "repo", "paper_url", "dataset_url", "model_url",
                    "exemplar_url", "exemplar", "reference_url"
                }:
                    add(v)
                walk(v)
            return

    seen = set()
    walk(obj)
    return urls
@dataclass
class LinkCheckResult:
    url: str
    final_url: str
    status: Optional[int]
    ok: bool
    redirect_chain: List[Dict[str, Any]]
    error: Optional[str]
    elapsed_ms: int
    last_checked: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "final_url": self.final_url,
            "status": self.status,
            "ok": self.ok,
            "redirect_chain": self.redirect_chain,
            "error": self.error,
            "elapsed_ms": self.elapsed_ms,
            "last_checked": self.last_checked,
        }


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None
def _request_once(url: str, method: str, timeout: float, headers: Dict[str, str]) -> Tuple[Optional[int], Dict[str, str], bytes]:
    req = urllib.request.Request(url, method=method, headers=headers)
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        with opener.open(req, timeout=timeout) as resp:
            status = getattr(resp, "status", None) or resp.getcode()
            hdrs = {k.lower(): v for k, v in resp.headers.items()}
            body = b""
            if method != "HEAD":
                body = resp.read(256)
            return int(status) if status is not None else None, hdrs, body
    except urllib.error.HTTPError as e:
        hdrs = {k.lower(): v for k, v in (e.headers.items() if e.headers else [])}
        return int(getattr(e, "code", 0) or 0), hdrs, b""
    except Exception as e:
        raise e


def check_url(
    url: str,
    timeout_s: float = 12.0,
    max_redirects: int = 8,
    retries: int = 2,
    retry_backoff_s: float = 0.6,
    headers: Optional[Dict[str, str]] = None,
) -> LinkCheckResult:
    start = time.time()
    base_headers = dict(_DEFAULT_HEADERS)
    if headers:
        base_headers.update(headers)

    chain: List[Dict[str, Any]] = []
    cur = _normalize_url(url)
    last_err: Optional[str] = None
    status: Optional[int] = None

    def attempt_request(u: str) -> Tuple[Optional[int], Dict[str, str], Optional[str]]:
        nonlocal last_err
        for i in range(retries + 1):
            try:
                st, hdrs, _ = _request_once(u, "HEAD", timeout_s, base_headers)
                if st in (405, 501) or st is None:
                    st, hdrs, _ = _request_once(u, "GET", timeout_s, base_headers)
                return st, hdrs, None
            except Exception as e:
                last_err = f"{type(e).__name__}: {e}"
                if i < retries:
                    time.sleep(retry_backoff_s * (2 ** i))
                else:
                    return None, {}, last_err
        return None, {}, last_err

    for _ in range(max_redirects + 1):
        st, hdrs, err = attempt_request(cur)
        status = st
        if err:
            break
        loc = hdrs.get("location")
        is_redirect = st is not None and st in (301, 302, 303, 307, 308) and loc
        chain.append({"url": cur, "status": st, "location": loc if loc else None})
        if is_redirect:
            nxt = urllib.parse.urljoin(cur, loc)
            if nxt == cur:
                break
            cur = _normalize_url(nxt)
            continue
        break

    elapsed_ms = int((time.time() - start) * 1000)
    ok = status is not None and 200 <= status < 400 and not last_err
    return LinkCheckResult(
        url=_normalize_url(url),
        final_url=cur,
        status=status,
        ok=bool(ok),
        redirect_chain=chain,
        error=last_err,
        elapsed_ms=elapsed_ms,
        last_checked=utc_now_iso(),
    )
def check_urls(
    urls: Iterable[str],
    **kwargs: Any,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen = set()
    for u in urls:
        u2 = _normalize_url(str(u))
        if not u2 or u2 in seen:
            continue
        seen.add(u2)
        out.append(check_url(u2, **kwargs).to_dict())
    return out


def build_report(
    results: List[Dict[str, Any]],
    source_files: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return {
        "generated_at": utc_now_iso(),
        "source_files": source_files or [],
        "counts": {
            "total": len(results),
            "ok": sum(1 for r in results if r.get("ok") is True),
            "broken": sum(1 for r in results if r.get("ok") is False),
            "redirected": sum(1 for r in results if (r.get("redirect_chain") or []) and (r.get("final_url") != r.get("url"))),
        },
        "results": results,
    }


def render_summary_md(report: Dict[str, Any]) -> str:
    c = report.get("counts") or {}
    lines = []
    lines.append("# Link Check Summary")
    lines.append("")
    lines.append(f"- Generated at: `{report.get('generated_at','')}`")
    sf = report.get("source_files") or []
    if sf:
        lines.append(f"- Case-study files scanned: `{len(sf)}`")
    lines.append(f"- Total URLs: `{c.get('total',0)}`")
    lines.append(f"- OK: `{c.get('ok',0)}`")
    lines.append(f"- Broken: `{c.get('broken',0)}`")
    lines.append(f"- Redirected: `{c.get('redirected',0)}`")
    lines.append("")
    lines.append("## Broken or suspicious links")
    lines.append("")
    broken = [r for r in (report.get('results') or []) if not r.get("ok")]
    if not broken:
        lines.append("None.")
    else:
        for r in broken[:200]:
            st = r.get("status")
            err = r.get("error")
            fin = r.get("final_url")
            u = r.get("url")
            lines.append(f"- `{st}` {u}")
            if fin and fin != u:
                lines.append(f"  - final: {fin}")
            if err:
                lines.append(f"  - error: {err}")
    lines.append("")
    lines.append("## Redirects (sample)")
    lines.append("")
    redir = [r for r in (report.get('results') or []) if (r.get("redirect_chain") or []) and (r.get("final_url") != r.get("url"))]
    if not redir:
        lines.append("None.")
    else:
        for r in redir[:50]:
            chain = r.get("redirect_chain") or []
            steps = " -> ".join([c.get("url","") for c in chain if c.get("url")])
            lines.append(f"- {steps} -> {r.get('final_url','')}")
    lines.append("")
    return "\n".join(lines)
