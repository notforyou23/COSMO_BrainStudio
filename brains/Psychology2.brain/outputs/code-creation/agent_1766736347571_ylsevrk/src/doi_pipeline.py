from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple
import json as _json, re, urllib.parse, urllib.request

FAIL = {
    "OK":"OK",
    "INVALID_DOI":"INVALID_DOI",
    "RESOLVE_FAILED":"RESOLVE_FAILED",
    "HTTP_ERROR":"HTTP_ERROR",
    "TIMEOUT":"TIMEOUT",
    "PAYWALL":"PAYWALL",
    "METADATA_NOT_FOUND":"METADATA_NOT_FOUND",
    "PARSE_FAILED":"PARSE_FAILED",
}

def utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def normalize_doi(doi: str) -> Optional[str]:
    if not doi: return None
    s = doi.strip()
    s = re.sub(r'^https?://(dx\.)?doi\.org/', '', s, flags=re.I)
    s = s.strip().strip('.')
    if not re.match(r'^10\.\d{4,9}/\S+$', s): return None
    return s.lower()

def _http(url: str, method: str="GET", headers: Optional[Dict[str,str]]=None, timeout: float=20.0) -> Tuple[int, str, Dict[str,str], bytes]:
    req = urllib.request.Request(url, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            b = r.read() if method != "HEAD" else b""
            h = {k.lower(): v for k, v in dict(r.headers).items()}
            return int(getattr(r, "status", 200)), str(r.geturl()), h, b
    except urllib.error.HTTPError as e:
        try:
            b = e.read() if method != "HEAD" else b""
        except Exception:
            b = b""
        h = {k.lower(): v for k, v in dict(getattr(e, "headers", {}) or {}).items()}
        return int(getattr(e, "code", 0) or 0), str(getattr(e, "url", url)), h, b
    except Exception as e:
        raise e

class _MetaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.m: Dict[str, List[str]] = {}
    def handle_starttag(self, tag, attrs):
        if tag.lower() != "meta": return
        d = {k.lower(): v for k, v in attrs if k}
        k = d.get("name") or d.get("property") or ""
        v = d.get("content") or ""
        if k and v:
            self.m.setdefault(k.strip().lower(), []).append(v.strip())

def _is_paywall(status: int, final_url: str, body: bytes, headers: Dict[str,str]) -> bool:
    if status in (401,403): return True
    if "text/html" not in (headers.get("content-type","").lower()): return False
    t = body[:200000].decode("utf-8", "ignore").lower()
    if any(x in final_url.lower() for x in ("login","signin","paywall","subscribe")): return True
    return any(x in t for x in ("purchase access","buy access","subscribe to access","institutional login","captcha","verify you are a human"))

def _norm_authors(a: Any) -> List[Dict[str,str]]:
    out=[]
    if isinstance(a, list):
        for x in a:
            if isinstance(x, dict):
                g=(x.get("given") or x.get("givenName") or "").strip()
                f=(x.get("family") or x.get("familyName") or x.get("name") or "").strip()
                name=(x.get("literal") or x.get("name") or "").strip()
                if not (g or f) and name: out.append({"name":name}); continue
                if g or f: out.append({"given":g,"family":f})
            elif isinstance(x, str) and x.strip():
                out.append({"name":x.strip()})
    return out

def _pick_year(obj: Any) -> Optional[int]:
    if isinstance(obj, dict):
        for k in ("published-print","published-online","published","issued","created"):
            v=obj.get(k)
            if isinstance(v, dict):
                dp=v.get("date-parts")
                if isinstance(dp, list) and dp and isinstance(dp[0], list) and dp[0]:
                    y=dp[0][0]
                    if isinstance(y, int): return y
    return None
@dataclass
class DOIResult:
    doi: str
    ok: bool
    record: Dict[str, Any]

class DOIPipeline:
    def __init__(self, user_agent: str="doi-pipeline/1.0 (mailto:unknown)"):
        self.ua = user_agent

    def resolve_landing(self, doi: str, timeout: float=20.0) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[str], Optional[bytes], Optional[Dict[str,str]]]:
        url = "https://doi.org/" + urllib.parse.quote(doi, safe="/")
        try:
            st, final_url, h, b = _http(url, "GET", {"User-Agent": self.ua, "Accept":"text/html,application/xhtml+xml"}, timeout)
            if st == 0: return None, None, None, FAIL["RESOLVE_FAILED"], None, None
            if _is_paywall(st, final_url, b, h): return final_url, final_url, st, FAIL["PAYWALL"], b, h
            if st >= 400: return final_url, final_url, st, FAIL["HTTP_ERROR"], b, h
            return final_url, final_url, st, None, b, h
        except TimeoutError:
            return None, None, None, FAIL["TIMEOUT"], None, None
        except Exception:
            return None, None, None, FAIL["RESOLVE_FAILED"], None, None

    def _crossref(self, doi: str, timeout: float=20.0) -> Tuple[Optional[Dict[str,Any]], Optional[str]]:
        u = "https://api.crossref.org/works/" + urllib.parse.quote(doi)
        try:
            st, final, h, b = _http(u, "GET", {"User-Agent": self.ua, "Accept":"application/json"}, timeout)
            if st != 200 or not b: return None, FAIL["METADATA_NOT_FOUND"]
            j = _json.loads(b.decode("utf-8","ignore"))
            m = (j or {}).get("message") or {}
            if not isinstance(m, dict) or not m: return None, FAIL["PARSE_FAILED"]
            title = (m.get("title") or [""])[0] if isinstance(m.get("title"), list) else (m.get("title") or "")
            rec = {
                "doi": doi,
                "title": title or None,
                "authors": _norm_authors(m.get("author")),
                "published_year": _pick_year(m) or None,
                "container_title": ((m.get("container-title") or [""])[0] if isinstance(m.get("container-title"), list) else m.get("container-title")) or None,
                "publisher": m.get("publisher") or None,
                "url": m.get("URL") or None,
                "source": "crossref",
            }
            return rec, None
        except Exception:
            return None, FAIL["PARSE_FAILED"]

    def _datacite(self, doi: str, timeout: float=20.0) -> Tuple[Optional[Dict[str,Any]], Optional[str]]:
        u = "https://api.datacite.org/dois/" + urllib.parse.quote(doi)
        try:
            st, final, h, b = _http(u, "GET", {"User-Agent": self.ua, "Accept":"application/vnd.api+json"}, timeout)
            if st != 200 or not b: return None, FAIL["METADATA_NOT_FOUND"]
            j = _json.loads(b.decode("utf-8","ignore"))
            a = (((j or {}).get("data") or {}).get("attributes") or {})
            if not isinstance(a, dict) or not a: return None, FAIL["PARSE_FAILED"]
            titles=a.get("titles") or []
            title=None
            if isinstance(titles, list) and titles:
                t0=titles[0] or {}
                if isinstance(t0, dict): title=t0.get("title")
            creators=a.get("creators") or []
            authors=[]
            if isinstance(creators, list):
                for c in creators:
                    if isinstance(c, dict):
                        n=c.get("name") or ""
                        g=c.get("givenName") or ""
                        f=c.get("familyName") or ""
                        if g or f: authors.append({"given":str(g).strip(),"family":str(f).strip()})
                        elif n: authors.append({"name":str(n).strip()})
            year=None
            pub=a.get("published") or a.get("publicationYear")
            if isinstance(pub, int): year=pub
            elif isinstance(pub, str) and pub[:4].isdigit(): year=int(pub[:4])
            rec = {
                "doi": doi,
                "title": title or None,
                "authors": authors,
                "published_year": year,
                "container_title": None,
                "publisher": a.get("publisher") or None,
                "url": (a.get("url") or None),
                "source": "datacite",
            }
            return rec, None
        except Exception:
            return None, FAIL["PARSE_FAILED"]

    def _embedded(self, doi: str, landing_url: str, html: bytes) -> Tuple[Optional[Dict[str,Any]], Optional[str]]:
        try:
            p=_MetaParser()
            p.feed(html.decode("utf-8","ignore"))
            m=p.m
            title=(m.get("citation_title") or m.get("dc.title") or m.get("og:title") or [None])[0]
            if not title: return None, FAIL["METADATA_NOT_FOUND"]
            authors=[{"name":a} for a in (m.get("citation_author") or []) if a]
            year=None
            y=(m.get("citation_publication_date") or m.get("citation_date") or m.get("dc.date") or [None])[0]
            if isinstance(y,str) and len(y)>=4 and y[:4].isdigit(): year=int(y[:4])
            cont=(m.get("citation_journal_title") or m.get("citation_conference_title") or m.get("citation_book_title") or [None])[0]
            pub=(m.get("citation_publisher") or m.get("dc.publisher") or [None])[0]
            rec={"doi":doi,"title":title,"authors":authors,"published_year":year,"container_title":cont,"publisher":pub,"url":landing_url,"source":"embedded"}
            return rec, None
        except Exception:
            return None, FAIL["PARSE_FAILED"]

    def process(self, doi_raw: str, timeout: float=20.0) -> DOIResult:
        accessed_at = utcnow_iso()
        doi = normalize_doi(doi_raw or "")
        prov = {"landing_url": None, "accessed_at": accessed_at, "parsing_method": None, "failure_reason_code": None}
        if not doi:
            prov["failure_reason_code"]=FAIL["INVALID_DOI"]
            return DOIResult(doi=doi_raw or "", ok=False, record={"doi":doi_raw, "provenance":prov})
        landing, final_url, st, fail, body, headers = self.resolve_landing(doi, timeout)
        prov["landing_url"] = final_url
        if fail:
            prov["failure_reason_code"]=fail
            return DOIResult(doi=doi, ok=False, record={"doi":doi, "provenance":prov})
        for method, fn in (("crossref", self._crossref), ("datacite", self._datacite)):
            rec, err = fn(doi, timeout)
            if rec:
                prov["parsing_method"]=method
                rec["provenance"]=prov
                return DOIResult(doi=doi, ok=True, record=rec)
        if body and final_url and headers and "text/html" in (headers.get("content-type","").lower()):
            rec, err = self._embedded(doi, final_url, body)
            if rec:
                prov["parsing_method"]="embedded_meta"
                rec["provenance"]=prov
                return DOIResult(doi=doi, ok=True, record=rec)
        prov["failure_reason_code"]=FAIL["METADATA_NOT_FOUND"]
        return DOIResult(doi=doi, ok=False, record={"doi":doi, "provenance":prov})

def process_dois(dois: List[str], user_agent: str="doi-pipeline/1.0 (mailto:unknown)", timeout: float=20.0) -> List[Dict[str,Any]]:
    p = DOIPipeline(user_agent=user_agent)
    return [p.process(d, timeout).record for d in (dois or [])]
