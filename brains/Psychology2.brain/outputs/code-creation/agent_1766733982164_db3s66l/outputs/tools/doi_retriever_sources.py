from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote, urlparse
import re
import time

DOI_RE = re.compile(r'(10\.[0-9]{4,9}/[-._;()/:A-Z0-9]+)', re.I)

def normalize_doi(raw: str) -> str:
    s = (raw or '').strip()
    s = re.sub(r'^https?://(dx\.)?doi\.org/', '', s, flags=re.I).strip()
    m = DOI_RE.search(s)
    return m.group(1).lower() if m else s.lower()

def _now_iso() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

def _host(u: str) -> str:
    try:
        return (urlparse(u).hostname or '').lower()
    except Exception:
        return ''

@dataclass
class Attempt:
    ts: str
    doi: str
    source: str
    url: Optional[str] = None
    ok: bool = False
    http_status: Optional[int] = None
    license: Optional[str] = None
    is_oa: Optional[bool] = None
    is_pd: Optional[bool] = None
    failure_code: Optional[str] = None
    failure_reason: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if d.get('meta') is None:
            d.pop('meta', None)
        return d

def _mk_attempt(doi: str, source: str, url: Optional[str]=None) -> Attempt:
    return Attempt(ts=_now_iso(), doi=doi, source=source, url=url)

def _license_flags(lic: Optional[str]) -> Tuple[Optional[bool], Optional[bool]]:
    if not lic:
        return None, None
    s = lic.strip().lower()
    is_pd = any(x in s for x in ('public domain', 'cc0', 'pdm', 'cc-0', 'cc0-1.0'))
    is_oa = True if ('cc' in s or 'open' in s or is_pd) else None
    return is_oa, is_pd
def query_unpaywall(doi: str, http_get, email: Optional[str]=None, timeout_s: float=20.0) -> List[Dict[str, Any]]:
    d = normalize_doi(doi)
    url = f'https://api.unpaywall.org/v2/{quote(d)}?email={quote(email or "anonymous@example.com")}'
    a = _mk_attempt(d, 'unpaywall', url=url)
    try:
        resp = http_get(url, timeout=timeout_s, headers={'Accept': 'application/json'})
        a.http_status = getattr(resp, 'status_code', None)
        if a.http_status and a.http_status >= 400:
            a.failure_code, a.failure_reason = 'http_error', f'HTTP {a.http_status}'
            return [a.to_dict()]
        data = resp.json() if hasattr(resp, 'json') else None
        best = (data or {}).get('best_oa_location') or {}
        oa_url = best.get('url_for_pdf') or best.get('url')
        lic = best.get('license') or (data or {}).get('license')
        a.url = oa_url or a.url
        a.license = lic
        a.is_oa = (data or {}).get('is_oa')
        if a.is_oa is None:
            a.is_oa, a.is_pd = _license_flags(lic)
        else:
            _, a.is_pd = _license_flags(lic)
        a.ok = bool(oa_url) or bool((data or {}).get('is_oa'))
        if not a.ok:
            a.failure_code, a.failure_reason = 'no_oa_location', 'No OA location found in Unpaywall'
        a.meta = {'host': _host(a.url) if a.url else None}
    except Exception as e:
        a.failure_code, a.failure_reason = 'exception', repr(e)
    return [a.to_dict()]
def query_crossref(doi: str, http_get, mailto: Optional[str]=None, timeout_s: float=20.0) -> List[Dict[str, Any]]:
    d = normalize_doi(doi)
    url = f'https://api.crossref.org/works/{quote(d)}'
    headers = {'Accept': 'application/json'}
    if mailto:
        headers['User-Agent'] = f'doi-retriever (mailto:{mailto})'
    a = _mk_attempt(d, 'crossref', url=url)
    try:
        resp = http_get(url, timeout=timeout_s, headers=headers)
        a.http_status = getattr(resp, 'status_code', None)
        if a.http_status and a.http_status >= 400:
            a.failure_code, a.failure_reason = 'http_error', f'HTTP {a.http_status}'
            return [a.to_dict()]
        j = resp.json() if hasattr(resp, 'json') else {}
        msg = (j or {}).get('message') or {}
        links = msg.get('link') or []
        pdf = None
        for lk in links:
            ct = (lk or {}).get('content-type', '') or ''
            if 'pdf' in ct.lower():
                pdf = (lk or {}).get('URL')
                break
        landing = msg.get('URL') or (f'https://doi.org/{d}' if d else None)
        a.meta = {'title': (msg.get('title') or [None])[0], 'publisher': msg.get('publisher'), 'host': _host(pdf or landing) if (pdf or landing) else None}
        a.url = pdf or landing or a.url
        a.ok = bool(a.url)
        if not a.ok:
            a.failure_code, a.failure_reason = 'no_url', 'No URL in Crossref record'
    except Exception as e:
        a.failure_code, a.failure_reason = 'exception', repr(e)
    return [a.to_dict()]
def repository_heuristics(doi: str) -> List[Dict[str, Any]]:
    d = normalize_doi(doi)
    out: List[Dict[str, Any]] = []
    def add(u: str, note: str):
        a = _mk_attempt(d, 'heuristic', url=u)
        a.ok = True
        a.meta = {'note': note, 'host': _host(u)}
        out.append(a.to_dict())

    if d:
        add(f'https://doi.org/{d}', 'doi_landing')

    m = re.match(r'^10\.48550/arxiv\.(\d{4}\.\d{4,5})(v\d+)?$', d, re.I)
    if m:
        aid = m.group(1) + (m.group(2) or '')
        add(f'https://arxiv.org/abs/{aid}', 'arxiv_abs')
        add(f'https://arxiv.org/pdf/{aid}.pdf', 'arxiv_pdf')

    m = re.match(r'^10\.(?:1101)/(\d{4}\.\d{2}\.\d{2}\.\d{6})(v\d+)?$', d, re.I)
    if m:
        sid = m.group(1) + (m.group(2) or '')
        add(f'https://www.biorxiv.org/content/{sid}v1', 'biorxiv_landing_guess')
        add(f'https://www.biorxiv.org/content/{sid}v1.full.pdf', 'biorxiv_pdf_guess')

    m = re.match(r'^10\.5281/zenodo\.(\d+)$', d, re.I)
    if m:
        zid = m.group(1)
        add(f'https://zenodo.org/record/{zid}', 'zenodo_landing')

    return out

def get_sources() -> Dict[str, Any]:
    return {'unpaywall': query_unpaywall, 'crossref': query_crossref, 'heuristic': repository_heuristics}
