#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys, time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError

UA = "cosmo-linkcheck/1.0 (+https://example.invalid)"
def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def _is_url(s: str) -> bool:
    try:
        u = urlparse(s)
        return u.scheme in ("http", "https") and bool(u.netloc)
    except Exception:
        return False

def _walk_json(x: Any) -> Iterable[str]:
    if isinstance(x, dict):
        for v in x.values():
            yield from _walk_json(v)
    elif isinstance(x, list):
        for v in x:
            yield from _walk_json(v)
    elif isinstance(x, str):
        if _is_url(x):
            yield x

def _extract_urls_from_case_json(data: Any) -> List[str]:
    urls = set(_walk_json(data))
    # common keys, if present
    if isinstance(data, dict):
        for k in ("exemplar_urls", "exemplarUrl", "exemplarURL", "urls", "links", "references"):
            v = data.get(k)
            if isinstance(v, str) and _is_url(v):
                urls.add(v)
            elif isinstance(v, list):
                for it in v:
                    if isinstance(it, str) and _is_url(it):
                        urls.add(it)
    return sorted(urls)
def _discover_case_json_files(root: Path) -> List[Path]:
    pats = [
        "**/*case*study*.json",
        "**/*case-study*.json",
        "**/*case_study*.json",
        "**/case_studies/*.json",
    ]
    seen = {}
    for pat in pats:
        for p in root.glob(pat):
            if p.is_file():
                seen[str(p.resolve())] = p
    return sorted(seen.values(), key=lambda x: str(x))

class _RedirectRecorder(HTTPRedirectHandler):
    def __init__(self):
        super().__init__()
        self.chain: List[Dict[str, Any]] = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.chain.append({"status_code": int(code), "from_url": req.full_url, "to_url": newurl})
        return super().redirect_request(req, fp, code, msg, headers, newurl)
@dataclass
class LinkCheckResult:
    url: str
    ok: bool
    status_code: Optional[int]
    final_url: Optional[str]
    redirects: List[Dict[str, Any]]
    error: Optional[str]
    last_checked: str
    source_files: List[str]

def _http_check(url: str, timeout_s: float, retries: int, sleep_s: float) -> Tuple[bool, Optional[int], Optional[str], List[Dict[str, Any]], Optional[str]]:
    last_err: Optional[str] = None
    for attempt in range(retries + 1):
        rr = _RedirectRecorder()
        opener = build_opener(rr)
        hdrs = {"User-Agent": UA, "Accept": "*/*"}
        for method in ("HEAD", "GET"):
            try:
                req = Request(url, headers=hdrs, method=method)
                resp = opener.open(req, timeout=timeout_s)
                code = getattr(resp, "status", None)
                final_url = getattr(resp, "geturl", lambda: None)()
                if hasattr(resp, "close"):
                    resp.close()
                ok = (code is not None) and (200 <= int(code) < 400)
                return ok, int(code) if code is not None else None, final_url, rr.chain, None
            except HTTPError as e:
                final_url = getattr(e, "geturl", lambda: None)()
                code = getattr(e, "code", None)
                last_err = f"HTTPError {code}: {getattr(e, 'reason', '')}".strip()
                if method == "GET" or (code is not None and int(code) < 500):
                    return False, int(code) if code is not None else None, final_url, rr.chain, last_err
            except URLError as e:
                last_err = f"URLError: {getattr(e, 'reason', e)}"
                break
            except Exception as e:
                last_err = f"{type(e).__name__}: {e}"
                break
        if attempt < retries:
            time.sleep(sleep_s)
    return False, None, None, [], last_err
def _md_summary(report: Dict[str, Any]) -> str:
    items = report.get("results", [])
    total = len(items)
    ok = sum(1 for r in items if r.get("ok"))
    bad = total - ok
    lines = []
    lines.append("# Link Check Summary")
    lines.append("")
    lines.append(f"- Generated: `{report.get('generated_at')}`")
    lines.append(f"- Total URLs: **{total}**")
    lines.append(f"- OK: **{ok}**")
    lines.append(f"- Problems: **{bad}**")
    lines.append("")
    if bad:
        lines.append("## Problems")
        lines.append("")
        lines.append("| URL | Status | Final URL | Error | Sources |")
        lines.append("|---|---:|---|---|---|")
        for r in items:
            if r.get("ok"):
                continue
            url = r.get("url","")
            sc = r.get("status_code")
            fu = r.get("final_url") or ""
            err = (r.get("error") or "").replace("
"," ").strip()
            src = ", ".join(r.get("source_files") or [])
            lines.append(f"| `{url}` | {sc if sc is not None else ''} | `{fu}` | {err} | {src} |")
        lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- Redirect chains are recorded per URL when available.")
    return "
".join(lines).rstrip() + "
"
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Check exemplar URLs referenced in case-study JSON files.")
    ap.add_argument("--root", default=None, help="Root directory to search for case-study JSON (default: project root).")
    ap.add_argument("--case-json", action="append", default=[], help="Explicit case-study JSON file path (repeatable).")
    ap.add_argument("--timeout", type=float, default=12.0)
    ap.add_argument("--retries", type=int, default=1)
    ap.add_argument("--sleep", type=float, default=0.5)
    args = ap.parse_args(argv)

    here = Path(__file__).resolve()
    project_root = Path(args.root).resolve() if args.root else here.parents[1]
    case_files = [Path(p).resolve() for p in args.case_json] if args.case_json else _discover_case_json_files(project_root)
    if not case_files:
        print("No case-study JSON files found.", file=sys.stderr)
    url_sources: Dict[str, set] = {}
    for cf in case_files:
        try:
            data = json.loads(cf.read_text(encoding="utf-8"))
        except Exception:
            continue
        for u in _extract_urls_from_case_json(data):
            url_sources.setdefault(u, set()).add(str(cf.relative_to(project_root)) if project_root in cf.parents else str(cf))

    results: List[Dict[str, Any]] = []
    for url, srcs in sorted(url_sources.items(), key=lambda kv: kv[0]):
        ok, sc, fu, redirs, err = _http_check(url, args.timeout, args.retries, args.sleep)
        res = LinkCheckResult(
            url=url, ok=ok, status_code=sc, final_url=fu,
            redirects=redirs, error=err, last_checked=_now_iso(),
            source_files=sorted(srcs),
        )
        results.append(asdict(res))

    out_dir = project_root / "runtime" / "outputs" / "qa"
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {"generated_at": _now_iso(), "root": str(project_root), "results": results}
    (out_dir / "linkcheck_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "
", encoding="utf-8")
    (out_dir / "LINKCHECK_SUMMARY.md").write_text(_md_summary(report), encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
